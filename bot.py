import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from fontes import buscar_todas
from ia import criar_materia_ia
from database import noticia_ja_vista, salvar_noticia, salvar_config, obter_config, obter_noticia_por_id

TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN não configurado.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    salvar_config("target_chat_id", chat_id)

    await update.message.reply_text(
        "📰 Radar Pop ativo!\n\n"
        "✅ Este chat foi definido para receber "
        "as notícias automaticamente."
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🟢 Radar funcionando normalmente."
    )



async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text(
        "🔎 Procurando novas notícias..."
    )

    try:
        noticias = buscar_todas()

        novas = [
            noticia
            for noticia in noticias
            if not noticia_ja_vista(noticia["url"])
        ]

        if not novas:
            await status_msg.edit_text(
                "✅ Nenhuma notícia nova encontrada."
            )
            return

        await status_msg.edit_text(
            f"📰 {len(novas)} conteúdo(s) novo(s) encontrado(s)."
        )

        # Máximo de 3 por busca.
        for noticia in reversed(novas[:3]):
            texto = (
                "🚨 NOVO CONTEÚDO\n\n"
                f"📰 {noticia['titulo']}\n\n"
                f"🌐 Fonte: {noticia['fonte']}\n"
                f"🕐 {noticia['publicado_em']}\n\n"
                f"🔗 {noticia['url']}"
            )

            noticia_id = salvar_noticia(
                noticia["fonte"],
                noticia["titulo"],
                noticia["url"],
                noticia["publicado_em"],
            )

            if not noticia_id:
                continue

            teclado = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✨ Criar matéria",
                        callback_data=f"criar_materia:{noticia_id}",
                    )
                ]
            ])

            await update.message.reply_text(
                texto,
                disable_web_page_preview=False,
                reply_markup=teclado,
            )

    except Exception as e:
        print(
            f"Erro ao buscar notícias: "
            f"{type(e).__name__}: {e}"
        )

        try:
            await status_msg.edit_text(
                "❌ Não consegui consultar as fontes agora."
            )
        except Exception:
            pass





async def testebotao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import conectar

    with conectar() as conn:
        resultado = conn.execute(
            "SELECT id FROM noticias ORDER BY id DESC LIMIT 1"
        ).fetchone()

    if not resultado:
        await update.message.reply_text(
            "❌ Nenhuma notícia encontrada no banco."
        )
        return

    noticia = obter_noticia_por_id(resultado[0])

    teclado = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✨ Criar matéria",
                callback_data=f"criar_materia:{noticia['id']}",
            )
        ]
    ])

    await update.message.reply_text(
        "🧪 TESTE DO BOTÃO\n\n"
        f"📰 {noticia['titulo']}\n\n"
        f"🌐 Fonte: {noticia['fonte']}\n\n"
        f"🔗 {noticia['url']}",
        disable_web_page_preview=False,
        reply_markup=teclado,
    )

async def ultimas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import conectar

    with conectar() as conn:
        resultados = conn.execute(
            """
            SELECT id
            FROM noticias
            ORDER BY id DESC
            LIMIT 5
            """
        ).fetchall()

    if not resultados:
        await update.message.reply_text(
            "❌ Nenhuma notícia encontrada no banco."
        )
        return

    await update.message.reply_text(
        "📰 Últimas notícias do Radar Pop:"
    )

    for resultado in resultados:
        noticia = obter_noticia_por_id(
            resultado[0]
        )

        if not noticia:
            continue

        teclado = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✨ Criar matéria",
                    callback_data=(
                        f"criar_materia:{noticia['id']}"
                    ),
                )
            ]
        ])

        await update.message.reply_text(
            f"📰 {noticia['titulo']}\n\n"
            f"🌐 Fonte: {noticia['fonte']}\n\n"
            f"🔗 {noticia['url']}",
            disable_web_page_preview=False,
            reply_markup=teclado,
        )


async def criar_materia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    try:
        await query.answer()
    except Exception as e:
        print(
            f"⚠️ Não foi possível responder ao callback: "
            f"{type(e).__name__}: {e}"
        )

    try:
        noticia_id = int(
            query.data.split(":", 1)[1]
        )
    except (ValueError, IndexError):
        await query.message.reply_text(
            "❌ Não consegui identificar esta notícia."
        )
        return

    noticia = obter_noticia_por_id(noticia_id)

    if not noticia:
        await query.message.reply_text(
            "❌ Esta notícia não foi encontrada no banco."
        )
        return

    status = await query.message.reply_text(
        "⏳ Lendo a matéria e criando a publicação...",
        reply_to_message_id=query.message.message_id,
    )

    try:
        materia = await asyncio.to_thread(
            criar_materia_ia,
            noticia["titulo"],
            noticia["fonte"],
            noticia["url"],
        )

        await status.edit_text(
            "✨ MATÉRIA CRIADA\n\n"
            f"📰 Original: {noticia['titulo']}\n"
            f"🌐 Fonte: {noticia['fonte']}\n\n"
            f"{materia}",
            disable_web_page_preview=True,
        )

    except Exception as e:
        print(
            f"❌ Erro ao criar matéria "
            f"{noticia_id}: {type(e).__name__}: {e}"
        )

        await status.edit_text(
            "❌ Não consegui criar a matéria. "
            "Tente novamente daqui a pouco."
        )


async def monitorar_noticias(context: ContextTypes.DEFAULT_TYPE):
    chat_id = obter_config("target_chat_id")

    if not chat_id:
        print("⚠️ Nenhum chat configurado. Use /start.")
        return

    try:
        noticias = buscar_todas()

        novas = [
            noticia
            for noticia in noticias
            if not noticia_ja_vista(noticia["url"])
        ]

        if not novas:
            print("🔎 Radar: nenhuma notícia nova.")
            return

        # Envia primeiro a notícia mais antiga entre as novas.
        for noticia in reversed(novas):
            texto = (
                "🚨 NOVA PUBLICAÇÃO\n\n"
                f"📰 {noticia['titulo']}\n\n"
                f"🌐 Fonte: {noticia['fonte']}\n"
                f"🕐 {noticia['publicado_em']}\n\n"
                f"🔗 {noticia['url']}"
            )

            noticia_id = salvar_noticia(
                noticia["fonte"],
                noticia["titulo"],
                noticia["url"],
                noticia["publicado_em"],
            )

            if not noticia_id:
                continue

            teclado = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✨ Criar matéria",
                        callback_data=f"criar_materia:{noticia_id}",
                    )
                ]
            ])

            await context.bot.send_message(
                chat_id=int(chat_id),
                text=texto,
                disable_web_page_preview=False,
                reply_markup=teclado,
            )

            print(
                f"📨 Enviado: {noticia['titulo']}"
            )

    except Exception as e:
        print(
            f"❌ Erro no Radar: "
            f"{type(e).__name__}: {e}"
        )


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(CommandHandler("testebotao", testebotao))
    app.add_handler(CommandHandler("ultimas", ultimas))
    app.add_handler(
        CallbackQueryHandler(
            criar_materia,
            pattern=r"^criar_materia:\d+$",
        )
    )

    app.job_queue.run_repeating(
        monitorar_noticias,
        interval=600,
        first=10,
        name="radar_pop",
    )

    async def configurar_menu(application):
        await application.bot.set_my_commands([
            BotCommand("start", "Iniciar o Radar Pop"),
            BotCommand("status", "Ver status do Radar"),
            BotCommand("buscar", "Buscar notícias novas"),
            BotCommand("ultimas", "Ver últimas notícias"),
        ])

    app.post_init = configurar_menu

    print("📰 Radar Pop iniciado...")
    app.run_polling()


if __name__ == "__main__":
    main()
