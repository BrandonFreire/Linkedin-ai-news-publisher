# Bot Automático para LinkedIn con IA (Gemini) y RSS

Este proyecto es un script en Python que automatiza la extracción de noticias desde fuentes RSS, procesa e interpreta el contenido usando la API de Gemini (modelo `gemini-2.5-flash`), y publica el resultado automáticamente en una página de empresa de LinkedIn. Está diseñado para ejecutarse de forma programada y gratuita mediante GitHub Actions.

## Arquitectura y Tecnologías
- **Lenguaje:** Python 3.12.10
- **Procesamiento de LLM:** SDK `google-genai` (Gemini 2.5 Flash)
- **Lector de Feeds:** `feedparser`
- **Peticiones HTTP:** `requests`
- **CI/CD & Cron Job:** GitHub Actions
- **Gestión de Entorno:** `python-dotenv` para desarrollo local y GitHub Secrets para producción.

## Estructura del Proyecto
- `main.py`: Lógica principal del script (extracción RSS, generación con IA, publicación en LinkedIn).
- `requirements.txt`: Dependencias de Python requeridas para el proyecto.
- `.env.example`: Plantilla de variables de entorno para configuración local.
- `.github/workflows/linkedin_bot.yml`: Flujo de trabajo automatizado para GitHub Actions.

## Configuración Local

1. Clona el repositorio:
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd <NOMBRE_DEL_REPOSITORIO>
   ```

2. Crea y activa un entorno virtual (recomendado):
   ```bash
   # En Windows:
   python -m venv venv
   venv\Scripts\activate
   
   # En Linux/Mac:
   python -m venv venv
   source venv/bin/activate
   ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Configura las variables de entorno:
   - Copia el archivo `.env.example` y renómbralo a `.env`:
     ```bash
     cp .env.example .env
     ```
   - Abre `.env` e inserta tus credenciales de la API de Gemini y de LinkedIn.

5. Ejecuta el script manualmente:
   ```bash
   python main.py
   ```

## Automatización con GitHub Actions

Para que el script se ejecute diariamente de manera automática:

1. Sube tu código a un repositorio en GitHub.
2. Ve a la pestaña **Settings** de tu repositorio.
3. Navega a **Secrets and variables > Actions**.
4. Añade los siguientes "Repository secrets" haciendo clic en "New repository secret":
   - `GEMINI_API_KEY`
   - `LINKEDIN_ACCESS_TOKEN`
   - `LINKEDIN_ORG_ID`
5. El bot se ejecutará automáticamente todos los días a las 09:00 UTC, tal como está definido en `.github/workflows/linkedin_bot.yml` (puedes modificar la expresión cron ahí si lo deseas).
6. También puedes disparar la ejecución manualmente desde la pestaña **Actions** seleccionando el workflow "LinkedIn RSS Bot" y haciendo clic en "Run workflow".
# Linkedin-ai-news-publisher
