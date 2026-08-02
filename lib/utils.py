from nanoid import generate


def model(table_name: str):
    def decorator(cls):
        cls.__TABLE_NAME__ = table_name
        return cls

    return decorator


def generate_room_code(size: int = 10) -> str:
    ALPHABET: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    return generate(alphabet=ALPHABET, size=size)
