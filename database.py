import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "radar.db"


def conectar():
    return sqlite3.connect(DB_PATH)


def criar_banco():
    with conectar() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS noticias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fonte TEXT NOT NULL,
                titulo TEXT,
                url TEXT NOT NULL UNIQUE,
                publicado_em TEXT,
                enviado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def noticia_ja_vista(url):
    with conectar() as conn:
        resultado = conn.execute(
            "SELECT 1 FROM noticias WHERE url = ? LIMIT 1",
            (url,)
        ).fetchone()

    return resultado is not None


def salvar_noticia(fonte, titulo, url, publicado_em=None):
    try:
        with conectar() as conn:
            cursor = conn.execute(
                """
                INSERT INTO noticias
                (fonte, titulo, url, publicado_em)
                VALUES (?, ?, ?, ?)
                """,
                (fonte, titulo, url, publicado_em)
            )

            noticia_id = cursor.lastrowid

        return noticia_id

    except sqlite3.IntegrityError:
        return False


criar_banco()



def obter_noticia_por_id(noticia_id):
    with conectar() as conn:
        conn.row_factory = sqlite3.Row

        resultado = conn.execute(
            """
            SELECT id, fonte, titulo, url, publicado_em
            FROM noticias
            WHERE id = ?
            """,
            (noticia_id,)
        ).fetchone()

    if not resultado:
        return None

    return dict(resultado)

def salvar_config(chave, valor):
    with conectar() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        """)

        conn.execute(
            """
            INSERT INTO configuracoes (chave, valor)
            VALUES (?, ?)
            ON CONFLICT(chave)
            DO UPDATE SET valor = excluded.valor
            """,
            (chave, str(valor))
        )


def obter_config(chave):
    with conectar() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        """)

        resultado = conn.execute(
            "SELECT valor FROM configuracoes WHERE chave = ?",
            (chave,)
        ).fetchone()

    return resultado[0] if resultado else None
