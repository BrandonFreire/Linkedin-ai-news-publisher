import os
import re
import requests
import feedparser
from dotenv import load_dotenv
from google import genai

# Cargar variables de entorno desde .env si existe
load_dotenv()

GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or "").strip()
GEMINI_MODEL = (os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash").strip()
LINKEDIN_ACCESS_TOKEN = (os.environ.get("LINKEDIN_ACCESS_TOKEN") or "").strip()
LINKEDIN_ORG_ID = (os.environ.get("LINKEDIN_ORG_ID") or "").strip()
LINKEDIN_API_VERSION = (
    os.environ.get("LINKEDIN_API_VERSION") or "202601"
).strip()

# URLs de feeds RSS a leer (Puedes configurar o agregar más)
RSS_FEEDS = [
    "https://feeds.feedburner.com/TechCrunch/",
    "https://www.theverge.com/rss/index.xml"
]

def fetch_latest_news():
    """Extrae la noticia más reciente de una lista de feeds RSS."""
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            if feed.entries:
                # Tomamos la noticia más reciente (la primera entrada)
                entry = feed.entries[0]
                title = entry.title
                link = entry.link
                summary = getattr(entry, 'summary', '')
                return title, link, summary
        except Exception as e:
            print(f"Error al leer el feed {feed_url}: {e}")
            continue
    return None, None, None

def generate_post_with_gemini(title, summary):
    """Genera un post corporativo para LinkedIn usando Gemini 2.5 Flash."""
    try:
        # Instanciar el cliente usando google-genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        
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
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return (response.text or "").strip()
    except Exception as e:
        print(f"Error al generar contenido con Gemini: {e}")
        return None

def post_to_linkedin_page(content, news_url):
    """Publica el contenido generado en una página de empresa de LinkedIn."""
    if not re.fullmatch(r"\d+", LINKEDIN_ORG_ID):
        print("Error: LINKEDIN_ORG_ID debe contener únicamente el ID numérico de la organización.")
        return False

    if not re.fullmatch(r"\d{6}", LINKEDIN_API_VERSION):
        print("Error: LINKEDIN_API_VERSION debe tener el formato YYYYMM, por ejemplo 202601.")
        return False

    try:
        url = "https://api.linkedin.com/rest/posts"
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
            "commentary": full_content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 201:
            print("Publicación exitosa en LinkedIn.")
            return True
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
        return False
    except requests.RequestException as e:
        print(f"Error de conexión con LinkedIn: {e}")
        return False
    except Exception as e:
        print(f"Excepción durante la publicación en LinkedIn: {e}")
        return False

if __name__ == "__main__":
    # Verificación de variables de entorno
    if not all([GEMINI_API_KEY, LINKEDIN_ACCESS_TOKEN, LINKEDIN_ORG_ID]):
        print("Error: Faltan variables de entorno necesarias (GEMINI_API_KEY, LINKEDIN_ACCESS_TOKEN, LINKEDIN_ORG_ID).")
        exit(1)
        
    print("Obteniendo última noticia del feed RSS...")
    title, link, summary = fetch_latest_news()
    
    if title and link:
        print(f"Noticia encontrada: {title}")
        print("Generando el texto del post con Gemini...")
        post_content = generate_post_with_gemini(title, summary)
        
        if post_content:
            print("Publicando en la página de empresa de LinkedIn...")
            if not post_to_linkedin_page(post_content, link):
                exit(1)
        else:
            print("No se pudo generar el contenido del post (el resultado de Gemini está vacío).")
            exit(1)
    else:
        print("No se encontraron noticias recientes en los feeds proporcionados o falló la conexión.")
