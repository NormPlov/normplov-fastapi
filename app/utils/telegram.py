import httpx
from app.core.config import settings

async def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            # Log the successful response
            print(f"Message sent successfully: {response.json()}")
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e}")
            print(f"Response: {response.text}")
        except Exception as ex:
            print(f"An unexpected error occurred: {ex}")
