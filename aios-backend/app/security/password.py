"""Password hashing. Isolated behind two functions so the hashing algorithm
(currently bcrypt via passlib) can be upgraded later — e.g. to argon2 — by
changing this file alone; nothing else in the codebase imports passlib
directly."""

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)
