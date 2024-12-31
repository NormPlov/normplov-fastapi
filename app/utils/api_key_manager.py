from itertools import cycle
from typing import List

class APIKeyManager:
    def __init__(self, api_keys: List[str]):
        if not api_keys or not isinstance(api_keys, list):
            raise ValueError("GOOGLE_GENERATIVE_AI_KEYS must be a non-empty list.")
        self.api_keys = cycle(api_keys)
        self.current_key = next(self.api_keys)

    def get_key(self) -> str:
        """Get the current API key."""
        return self.current_key

    def switch_key(self) -> str:
        """Switch to the next API key."""
        self.current_key = next(self.api_keys)
        return self.current_key
