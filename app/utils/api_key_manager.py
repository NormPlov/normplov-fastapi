from typing import List
from itertools import cycle
from app.core.config import settings


class APIKeyManager:
    def __init__(self, api_keys: List[str]):
        if not api_keys:
            raise ValueError("No API keys provided for Google Generative AI.")
        self.api_keys = cycle(api_keys)
        self.current_key = next(self.api_keys)

    def switch_key(self):
        self.current_key = next(self.api_keys)
        return self.current_key

api_key_manager = APIKeyManager(settings.GOOGLE_GENERATIVE_AI_KEYS)
