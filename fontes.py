import feedparser
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin


FONTES = {
    "Den of Geek": {
        "feed": "https://www.denofgeek.com/feed/",
        "idioma": "en",
    },
}


def buscar_den_of_geek():
    fonte = FONTES["Den of Geek"]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 11) "
            "AppleWebKit/537.36 "
            "Chrome/140.0 Mobile Safari/537.36"
        )
    }

    ultimo_erro = None

    for tentativa in range(3):
        try:
            resposta = requests.get(
                fonte["feed"],
                headers=headers,
                timeout=20,
            )

            resposta.raise_for_status()

            feed = feedparser.parse(resposta.content)

            if not feed.entries:
                raise RuntimeError(
                    "O feed respondeu, mas não trouxe notícias."
                )

            break

        except Exception as e:
            ultimo_erro = e

            if tentativa < 2:
                time.sleep(3)

    else:
        raise RuntimeError(
            f"Falha ao consultar Den of Geek: {ultimo_erro}"
        )

    noticias = []

    for item in feed.entries:
        titulo = item.get("title", "").strip()
        url = item.get("link", "").strip()
        publicado = item.get("published", "")

        categorias = [
            tag.get("term", "").strip()
            for tag in item.get("tags", [])
        ]

        # Conteúdos MSN são listas/curiosidades genéricas
        # que não interessam ao Radar Pop.
        if "MSN" in categorias:
            continue

        if not titulo or not url:
            continue

        noticias.append({
            "fonte": "Den of Geek",
            "titulo": titulo,
            "url": url,
            "publicado_em": publicado,
            "idioma": "en",
        })

    return noticias


def buscar_omelete():
    url = "https://www.omelete.com.br/noticias"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 11) "
            "AppleWebKit/537.36 "
            "Chrome/140.0 Mobile Safari/537.36"
        )
    }

    ultimo_erro = None

    for tentativa in range(3):
        try:
            resposta = requests.get(
                url,
                headers=headers,
                timeout=20,
            )

            resposta.raise_for_status()
            break

        except Exception as e:
            ultimo_erro = e

            if tentativa < 2:
                time.sleep(3)

    else:
        raise RuntimeError(
            f"Falha ao consultar Omelete: {ultimo_erro}"
        )

    soup = BeautifulSoup(resposta.text, "html.parser")

    noticias = []
    urls_vistas = set()

    for article in soup.select("article.card--news"):
        link_tag = article.select_one("a.card__link[href]")
        titulo_tag = article.select_one("h2.card__title")

        if not link_tag or not titulo_tag:
            continue

        titulo = titulo_tag.get_text(" ", strip=True)
        link = urljoin(url, link_tag.get("href", "")).strip()

        if not titulo or not link:
            continue

        if link in urls_vistas:
            continue

        urls_vistas.add(link)

        categoria_tag = article.select_one(".badge")
        categoria = (
            categoria_tag.get_text(" ", strip=True)
            if categoria_tag
            else ""
        )

        data_tag = article.select_one(
            ".card__published-time[data-published]"
        )

        publicado = (
            data_tag.get("data-published", "").strip()
            if data_tag
            else ""
        )

        imagem_tag = article.select_one("img")
        imagem = ""

        if imagem_tag:
            imagem = (
                imagem_tag.get("data-lazy-src")
                or imagem_tag.get("src")
                or ""
            ).strip()

            if imagem.startswith("//"):
                imagem = "https:" + imagem

        noticias.append({
            "fonte": "Omelete",
            "titulo": titulo,
            "url": link,
            "publicado_em": publicado,
            "idioma": "pt-BR",
            "categoria": categoria,
            "imagem": imagem,
        })

    return noticias



def buscar_cnn_pop():
    url = "https://www.cnnbrasil.com.br/pop/"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 11) "
            "AppleWebKit/537.36 "
            "Chrome/140.0 Mobile Safari/537.36"
        )
    }

    ultimo_erro = None

    for tentativa in range(3):
        try:
            resposta = requests.get(
                url,
                headers=headers,
                timeout=20,
            )

            resposta.raise_for_status()
            break

        except Exception as e:
            ultimo_erro = e

            if tentativa < 2:
                time.sleep(3)

    else:
        raise RuntimeError(
            f"Falha ao consultar CNN Pop: {ultimo_erro}"
        )

    soup = BeautifulSoup(resposta.text, "html.parser")

    noticias = []
    urls_vistas = set()

    for link_tag in soup.find_all("a", href=True):
        link = urljoin(url, link_tag["href"]).strip()

        # Aceita somente matérias da editoria Pop.
        if not link.startswith(
            "https://www.cnnbrasil.com.br/pop/"
        ):
            continue

        # Ignora a própria página da editoria.
        if link.rstrip("/") == url.rstrip("/"):
            continue

        if link in urls_vistas:
            continue

        titulo_tag = link_tag.find(["h1", "h2", "h3"])

        if titulo_tag:
            titulo = titulo_tag.get_text(" ", strip=True)
        else:
            imagem_tag = link_tag.find("img")
            titulo = (
                imagem_tag.get("alt", "").strip()
                if imagem_tag
                else ""
            )

        prefixo = "Imagem de destaque do post:"

        if titulo.startswith(prefixo):
            titulo = titulo[len(prefixo):].strip()

        if len(titulo) < 15:
            continue

        urls_vistas.add(link)

        partes = link.replace(
            "https://www.cnnbrasil.com.br/pop/",
            ""
        ).split("/")

        categoria = (
            partes[0].replace("-", " ").title()
            if partes and partes[0]
            else "Pop"
        )

        imagem = ""
        imagem_tag = link_tag.find("img")

        if imagem_tag:
            imagem = (
                imagem_tag.get("src")
                or imagem_tag.get("data-src")
                or ""
            ).strip()

        noticias.append({
            "fonte": "CNN Pop",
            "titulo": titulo,
            "url": link,
            "publicado_em": "",
            "idioma": "pt-BR",
            "categoria": categoria,
            "imagem": imagem,
        })

    return noticias


def buscar_adorocinema():
    paginas = [
        (
            "https://www.adorocinema.com/noticias/filmes/",
            "Filmes",
            "/noticias/filmes/noticia-",
        ),
        (
            "https://www.adorocinema.com/noticias/series/",
            "Séries",
            "/noticias/series/noticia-",
        ),
    ]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 11) "
            "AppleWebKit/537.36 "
            "Chrome/140.0 Mobile Safari/537.36"
        )
    }

    noticias = []
    urls_vistas = set()

    for url, categoria, padrao in paginas:
        ultimo_erro = None

        for tentativa in range(3):
            try:
                resposta = requests.get(
                    url,
                    headers=headers,
                    timeout=20,
                )

                resposta.raise_for_status()
                break

            except Exception as e:
                ultimo_erro = e

                if tentativa < 2:
                    time.sleep(3)

        else:
            print(
                f"⚠️ AdoroCinema {categoria}: "
                f"{ultimo_erro}"
            )
            continue

        soup = BeautifulSoup(
            resposta.text,
            "html.parser"
        )

        for link_tag in soup.select(
            "a.meta-title-link[href]"
        ):
            href = link_tag.get("href", "").strip()

            if not href.startswith(padrao):
                continue

            titulo = link_tag.get_text(
                " ",
                strip=True
            )

            link = urljoin(url, href)

            if not titulo or link in urls_vistas:
                continue

            urls_vistas.add(link)

            noticias.append({
                "fonte": "AdoroCinema",
                "titulo": titulo,
                "url": link,
                "publicado_em": "",
                "idioma": "pt-BR",
                "categoria": categoria,
                "imagem": "",
            })

    return noticias


def buscar_gq():
    url = "https://www.gq.com/entertainment"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 11) "
            "AppleWebKit/537.36 "
            "Chrome/140.0 Mobile Safari/537.36"
        )
    }

    ultimo_erro = None

    for tentativa in range(3):
        try:
            resposta = requests.get(
                url,
                headers=headers,
                timeout=20,
            )
            resposta.raise_for_status()
            break

        except Exception as e:
            ultimo_erro = e

            if tentativa < 2:
                time.sleep(3)

    else:
        raise RuntimeError(
            f"Falha ao consultar GQ: {ultimo_erro}"
        )

    soup = BeautifulSoup(
        resposta.text,
        "html.parser"
    )

    noticias = []
    urls_vistas = set()

    for link_tag in soup.select(
        "a.summary-item__hed-link[href]"
    ):
        href = link_tag.get("href", "").strip()

        if not href.startswith("/story/"):
            continue

        titulo_tag = link_tag.select_one(
            ".summary-item__hed"
        )

        if titulo_tag:
            titulo = titulo_tag.get_text(
                " ",
                strip=True
            )
        else:
            titulo = link_tag.get_text(
                " ",
                strip=True
            )

        if len(titulo) < 15:
            continue

        link = urljoin(
            "https://www.gq.com",
            href
        )

        if link in urls_vistas:
            continue

        urls_vistas.add(link)

        card = link_tag.find_parent(
            class_=lambda c:
                c and "summary-item" in str(c).lower()
        )

        categoria = "Entertainment"

        if card:
            rubric = card.select_one(
                ".rubric__name"
            )

            if rubric:
                categoria = rubric.get_text(
                    " ",
                    strip=True
                )

        if categoria.lower() != "culture":
            continue

        noticias.append({
            "fonte": "GQ",
            "titulo": titulo,
            "url": link,
            "publicado_em": "",
            "idioma": "en",
            "categoria": categoria,
            "imagem": "",
        })

    return noticias

def buscar_todas():
    coletores = [
        ("Den of Geek", buscar_den_of_geek),
        ("Omelete", buscar_omelete),
        ("CNN Pop", buscar_cnn_pop),
        ("AdoroCinema", buscar_adorocinema),
        ("GQ", buscar_gq),
    ]

    todas = []

    for nome, coletor in coletores:
        try:
            noticias = coletor()
            todas.extend(noticias)

            print(
                f"✅ {nome}: "
                f"{len(noticias)} conteúdo(s)"
            )

        except Exception as e:
            # Uma fonte com problema não derruba as outras.
            print(
                f"⚠️ {nome}: "
                f"{type(e).__name__}: {e}"
            )

    return todas
