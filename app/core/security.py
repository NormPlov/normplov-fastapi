from passlib.context import CryptContext
import random

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def generate_verification_code(length: int = 6) -> str:
    return ''.join(random.choices("0123456789", k=length))

def generate_reset_code(length: int = 6) -> str:
    return ''.join(random.choices("0123456789", k=length))