import os
import re
import json
import calendar
import requests
import feedparser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from dotenv import load_dotenv
from google import genai

# Cargar variables de entorno desde .env si existe
load_dotenv(override=True)

GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or "").strip()
GEMINI_MODEL = (os.environ.get("GEMINI_MODEL") or "gemini-3.5-flash").strip()
LINKEDIN_ACCESS_TOKEN = (os.environ.get("LINKEDIN_ACCESS_TOKEN") or "").strip()
LINKEDIN_ORG_ID = (os.environ.get("LINKEDIN_ORG_ID") or "").strip()
LINKEDIN_API_VERSION = (
    os.environ.get("LINKEDIN_API_VERSION") or "202601"
).strip()
PUBLISHED_NEWS_FILE = Path(
    os.environ.get("PUBLISHED_NEWS_FILE") or "data/published_news.json"
)

# URLs de feeds RSS a leer
'''
RSS_FEEDS = [
    "https://feeds.feedburner.com/TechCrunch/",
    "https://www.theverge.com/rss/index.xml"
]
'''

RSS_FEEDS = [
    # Agua, pérdidas no técnicas y agua inteligente
    "https://smartwatermagazine.com/rss.xml",
    "https://www.waterworld.com/rss",
    
    # GIS, Teledetección y Observación de la Tierra
    "https://www.gisuser.com/feed/",
    "https://earthobservatory.nasa.gov/feeder/blogs.xml",
    "https://www.gim-international.com/rss/news"
]

def normalize_news_url(url):
    """Normaliza una URL para detectar la misma noticia con tracking distinto."""
    parsed_url = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parsed_url.query, keep_blank_values=True)
        if not key.lower().startswith(("utm_", "fbclid", "gclid"))
    ]
    return urlunsplit((
        parsed_url.scheme.lower(),
        parsed_url.netloc.lower(),
        parsed_url.path.rstrip("/") or "/",
        urlencode(query),
        "",
    ))

def load_published_news():
    """Carga las URLs publicadas; si no existe estado, inicia un registro vacío."""
    try:
        if not PUBLISHED_NEWS_FILE.exists():
            return set()
        data = json.loads(PUBLISHED_NEWS_FILE.read_text(encoding="utf-8"))
        urls = data.get("published_urls", [])
        if not isinstance(urls, list):
            raise ValueError("published_urls debe ser una lista")
        return {normalize_news_url(url) for url in urls if isinstance(url, str)}
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"Error al cargar el registro de noticias publicadas: {e}")
        return None

def save_published_news(published_urls):
    """Guarda el registro de forma atómica para no dejar JSON incompleto."""
    try:
        PUBLISHED_NEWS_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = PUBLISHED_NEWS_FILE.with_suffix(".tmp")
        payload = {"published_urls": sorted(published_urls)[-500:]}
        temporary_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_file.replace(PUBLISHED_NEWS_FILE)
    except OSError as e:
        print(f"Error al guardar el registro de noticias publicadas: {e}")
        return False
    return True

def fetch_latest_news(published_urls):
    """Devuelve la noticia más reciente que todavía no se ha publicado."""
    candidates = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "").strip()
                if not title or not link:
                    continue
                normalized_link = normalize_news_url(link)
                if normalized_link in published_urls:
                    continue
                published_timestamp = getattr(entry, "published_parsed", None)
                timestamp = (
                calendar.timegm(published_timestamp)
                if published_timestamp
                else 0
                )
                candidates.append((
                    timestamp,
                    title,
                    link,
                    getattr(entry, "summary", ""),
                ))
        except Exception as e:
            print(f"Error al leer el feed {feed_url}: {e}")
            continue
    if not candidates:
        return None, None, None
    _, title, link, summary = max(candidates, key=lambda candidate: candidate[0])
    return title, link, summary

def generate_post_with_gemini(title, summary):
    """Genera un post corporativo para LinkedIn usando Gemini 3.5 Flash."""
    try:
        # Instanciar el cliente usando google-genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        '''
        prompt = f"""
        Actúa como un Community Manager experto.
        A partir del siguiente titular y resumen de una noticia tecnológica/empresarial, redacta un post corporativo para LinkedIn.
        El post debe cumplir las siguientes reglas:
        - Tener un máximo de 120 palabras.
        - Usar un tono profesional pero atractivo.
        - Incluir 3-4 hashtags relevantes al final.
        - Terminar con una pregunta de cierre que invite a la interacción de los seguidores.
        
        Titular: {title}
        Resumen: {summary}
        """
        '''

        prompt = f"""

                Actúa como el Director de Comunicación y Marketing Técnico para SOINNTECH. Eres experto en teledetección satelital, geofonamiento, catastro de redes de agua potable, alcantarillado y balances hídricos en América Latina.
                
                Redacta una publicación profesional para LinkedIn (entre 150 y 200 palabras) basada en la siguiente noticia, conectando el tema con la propuesta de valor y tecnologías de SOINNTECH.

                ESTRUCTURA DEL POST:
                1. Gancho inicial: Menciona un dato o reflexión destacada de la noticia en 1-2 oraciones.
                2. Puente con SOINNTECH: Explica brevemente cómo la teledetección satelital, la IA o la digitalización de infraestructuras de SOINNTECH abordan este tipo de retos técnicos.
                3. Llamado a la acción (CTA): Invita a reflexionar o visitar https://soinntech.com para conocer más sobre nuestras soluciones.
                4. Cierre con 3 a 5 hashtags relevantes e interesantes (ej. #AguaPotable #Teledetección #IA #Infraestructura #SOINNTECH).

                DATOS DE LA NOTICIA:
                Título: {title}
                Descripción: {summary}                           
                """

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return (response.text or "").strip()
    except Exception as e:
        print(f"Error al generar contenido con Gemini: {e}")
        return None

def post_to_linkedin_page(content, news_url):
    """Publica en LinkedIn y devuelve la URL del post creado."""
    if not re.fullmatch(r"\d+", LINKEDIN_ORG_ID):
        print("Error: LINKEDIN_ORG_ID debe contener únicamente el ID numérico de la organización.")
        return None

    if not re.fullmatch(r"\d{6}", LINKEDIN_API_VERSION):
        print("Error: LINKEDIN_API_VERSION debe tener el formato YYYYMM, por ejemplo 202601.")
        return None

    try:
        #url = "https://api.linkedin.com/rest/posts"
        url = "https://api.linkedin.com/v2/ugcPosts"

        headers = {
            "Authorization": "Bearer " + LINKEDIN_ACCESS_TOKEN,
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": LINKEDIN_API_VERSION,
            "Content-Type": "application/json"
        }
        
        # Agregamos la URL al final del texto generado
        full_content = f"{content}\n\nFuente: {news_url}"
        
        payload = {
            "author": f"urn:li:organization:{LINKEDIN_ORG_ID}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": full_content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 201:
            print("Publicación exitosa en LinkedIn.")
            post_id = response.headers.get("x-restli-id")
            if not post_id:
                print(
                    "LinkedIn publicó el contenido, pero no devolvió el identificador "
                    "del post; no se podrá enlazar desde Telegram."
                )
                return None

            linkedin_post_url = f"https://www.linkedin.com/feed/update/{post_id}"
            print(f"URL de la publicación: {linkedin_post_url}")
            return linkedin_post_url
        elif response.status_code == 401:
            print(
                "LinkedIn rechazó el access token (401 AUTHENTICATION_FAILED). "
                "LINKEDIN_ACCESS_TOKEN debe ser un token OAuth de LinkedIn vigente; "
                "una API key de Gemini no sirve aquí. Genera uno nuevo y vuelve a "
                "autorizar la aplicación."
            )
            print(f"Detalle de LinkedIn: {response.text}")
        elif response.status_code in (403, 422):
            print(
                f"LinkedIn rechazó la publicación (HTTP {response.status_code}). "
                "Verifica que el usuario sea administrador de la organización y que "
                "el token tenga el permiso w_organization_social."
            )
            print(f"Detalle de LinkedIn: {response.text}")
        else:
            print(f"Error al publicar en LinkedIn. HTTP {response.status_code}: {response.text}")
        return None
    except requests.RequestException as e:
        print(f"Error de conexión con LinkedIn: {e}")
        return None
    except Exception as e:
        print(f"Excepción durante la publicación en LinkedIn: {e}")
        return None

def notify_telegram(news_title: str, linkedin_post_url: str = "", post_content: str=""):
    """Notifica enviada por Telegram después de publicar correctamente en LinkedIn."""
    bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()

    if not bot_token or not chat_id:
        print(
            "Notificación de Telegram omitida: faltan TELEGRAM_BOT_TOKEN "
            "o TELEGRAM_CHAT_ID."
        )
        return False

    message = (
        f"🚀 *¡Nuevo post publicado en LinkedIn!*\n\n"
        f"📌 *Noticia:* {news_title}\n"
        f"✅ *Estado:* Publicado exitosamente en la página de empresa."
        f"\n\n💬 *Contenido del post:*\n{post_content}"
    )
    if linkedin_post_url:
        message += f"\n🔗 [Ver publicación en LinkedIn]({linkedin_post_url})"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("Notificación enviada correctamente por Telegram.")
            return True

        print(
            f"Telegram rechazó la notificación (HTTP {response.status_code}): "
            f"{response.text}"
        )
    except requests.RequestException as e:
        print(f"Error de conexión con Telegram: {e}")
    return False

if __name__ == "__main__":
    # Verificación de variables de entorno
    if not all([GEMINI_API_KEY, LINKEDIN_ACCESS_TOKEN, LINKEDIN_ORG_ID]):
        print("Error: Faltan variables de entorno necesarias (GEMINI_API_KEY, LINKEDIN_ACCESS_TOKEN, LINKEDIN_ORG_ID).")
        exit(1)
        
    published_urls = load_published_news()
    if published_urls is None:
        exit(1)

    print("Obteniendo la noticia más reciente no publicada del feed RSS...")
    title, link, summary = fetch_latest_news(published_urls)
    
    if title and link:
        print(f"Noticia encontrada: {title}")
        print("Generando el texto del post con Gemini...")
        post_content = generate_post_with_gemini(title, summary)
        
        if post_content:
            print("Publicando en la página de empresa de LinkedIn...")
            linkedin_post_url = post_to_linkedin_page(post_content, link)
            if not linkedin_post_url:
                exit(1)

            published_urls.add(normalize_news_url(link))
            if not save_published_news(published_urls):
                exit(1)
            notify_telegram(title, linkedin_post_url=linkedin_post_url, post_content=post_content)
        else:
            print("No se pudo generar el contenido del post (el resultado de Gemini está vacío).")
            exit(1)
    else:
        print("No se encontraron noticias recientes en los feeds proporcionados o falló la conexión.")
