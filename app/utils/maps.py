from urllib.parse import urlencode
from app.core.config import settings


def generate_google_map_embed_url(latitude: float, longitude: float) -> str:

    api_key = settings.GOOGLE_GENERATIVE_AI_KEY
    base_url = "https://www.google.com/maps/embed/v1/place"
    params = {
        "key": api_key,
        "q": f"{latitude},{longitude}"
    }
    return f"{base_url}?{urlencode(params)}"
