import bcrypt

def is_bcrypt_hash(s: str) -> bool:
    """Проверяет, является ли строка валидным bcrypt-хешем."""
    return (
        isinstance(s, str)
        and len(s) == 60
        and s.startswith(("$2b$", "$2a$", "$2y$"))
    )

def hash_password(password: str) -> str:
    """Хеширует пароль с использованием bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def check_password(plain_password: str, stored_password: str) -> bool:
    """
    Проверяет пароль.
    Поддерживает:
      - bcrypt-хеши (новые пользователи)
      - plaintext (старые пользователи)
    """
    if is_bcrypt_hash(stored_password):
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                stored_password.encode("utf-8")
            )
        except ValueError:
            return False
    else:
        return plain_password == stored_password