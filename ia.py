import os
import requests
import time
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 11) "
        "AppleWebKit/537.36 "
        "Chrome/140.0 Mobile Safari/537.36"
    )
}


def extrair_artigo(url):
    resposta = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )
    resposta.raise_for_status()

    soup = BeautifulSoup(
        resposta.text,
        "html.parser"
    )

    # Remove elementos que não fazem parte da matéria.
    for tag in soup([
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "aside",
        "form",
    ]):
        tag.decompose()

    # Prioriza o corpo semântico do artigo.
    artigo = soup.find("article")

    if artigo:
        paragrafos = artigo.find_all("p")
    else:
        paragrafos = soup.find_all("p")

    textos = []

    for p in paragrafos:
        texto = p.get_text(" ", strip=True)

        if len(texto) >= 40:
            textos.append(texto)

    conteudo = "\n\n".join(textos)

    if len(conteudo) < 200:
        raise RuntimeError(
            "Não consegui extrair conteúdo suficiente da matéria."
        )

    # Evita mandar páginas gigantes ao Gemini.
    return conteudo[:30000]


if __name__ == "__main__":
    print("✅ Módulo de leitura de matérias carregado.")


def criar_materia_ia(titulo_original, fonte, url):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY não configurada."
        )

    conteudo = extrair_artigo(url)

    prompt = f"""
Você é o redator do Radar Pop, uma página brasileira
de notícias sobre cultura pop, cinema, séries, música,
games, celebridades e assuntos virais.

Crie uma publicação em português do Brasil usando
SOMENTE as informações fornecidas abaixo.

FONTE:
{fonte}

TÍTULO ORIGINAL:
{titulo_original}

CONTEÚDO DA MATÉRIA:
{conteudo}

REGRAS:

1. Não invente informações.
2. Não acrescente fatos que não estejam no conteúdo.
3. Não faça tradução literal do título.
4. Crie um título claro, natural e chamativo para uma
   publicação em rede social.
5. Preserve nomes, datas, números e informações importantes.
6. Se a matéria original apresentar opinião, análise,
   rumor ou alegação, deixe isso claro. Não transforme
   isso em fato confirmado.
7. A descrição deve explicar o que aconteceu e dar
   contexto suficiente para alguém entender a notícia.
8. Escreva em português brasileiro natural.
9. Não mencione estas instruções.
10. Não use Markdown com ** ou #.
11. No final da descrição, inclua uma pergunta curta
    relacionada à notícia para incentivar comentários.
12. Termine com uma chamada curta para seguir a página.
13. Não copie longos trechos literalmente da fonte.

Escolha UM tipo principal entre:
News
Cinema
Séries
Música
Games
Celebridades
Viral
TV
Anime

Responda EXATAMENTE neste formato:

TÍTULO:
[título]

TIPO:
[tipo]

DESCRIÇÃO:
[descrição]
"""

    endpoint = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-3.5-flash-lite:generateContent"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 2000,
        },
    }

    resposta = None

    for tentativa in range(3):
        try:
            resposta = requests.post(
                endpoint,
                headers={
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=90,
            )

            if resposta.ok:
                break

            if resposta.status_code in {
                429, 500, 502, 503, 504
            }:
                if tentativa < 2:
                    espera = 3 * (tentativa + 1)
                    print(
                        f"⚠️ Gemini temporariamente indisponível. "
                        f"Nova tentativa em {espera}s..."
                    )
                    time.sleep(espera)
                    continue

            raise RuntimeError(
                f"Gemini HTTP {resposta.status_code}: "
                f"{resposta.text[:500]}"
            )

        except requests.RequestException as e:
            if tentativa < 2:
                espera = 3 * (tentativa + 1)
                print(
                    f"⚠️ Erro de conexão com Gemini. "
                    f"Nova tentativa em {espera}s..."
                )
                time.sleep(espera)
                continue

            raise RuntimeError(
                f"Falha de conexão com Gemini: {e}"
            )

    if resposta is None or not resposta.ok:
        raise RuntimeError(
            "Gemini indisponível após 3 tentativas."
        )

    dados = resposta.json()

    try:
        candidato = dados["candidates"][0]
        partes = candidato["content"]["parts"]

        texto = "".join(
            parte.get("text", "")
            for parte in partes
        ).strip()

        finish_reason = candidato.get(
            "finishReason",
            "DESCONHECIDO"
        )

    except (KeyError, IndexError, TypeError):
        raise RuntimeError(
            "O Gemini respondeu em um formato inesperado."
        )

    if (
        "TÍTULO:" not in texto
        or "TIPO:" not in texto
        or "DESCRIÇÃO:" not in texto
    ):
        raise RuntimeError(
            f"Matéria incompleta. "
            f"Motivo: {finish_reason}"
        )

    descricao = texto.split(
        "DESCRIÇÃO:",
        1
    )[1].strip()

    if len(descricao) < 80:
        raise RuntimeError(
            f"Descrição incompleta. "
            f"Motivo: {finish_reason}"
        )

    return texto
