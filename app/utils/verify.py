import uuid


def is_valid_uuid(value: str) -> bool:
    try:
        uuid_obj = uuid.UUID(value, version=4)
    except ValueError:
        return False
    return str(uuid_obj) == value
