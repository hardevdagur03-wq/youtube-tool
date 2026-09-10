"""Password hashing and validation service.

Uses bcrypt with strong parameters for all password operations.
"""

from __future__ import annotations

import bcrypt
import re

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]"
)


class PasswordService:
    """Handles password hashing, verification, and strength validation."""

    ROUNDS = 12

    @staticmethod
    def hash_password(password: str) -> str:
        if not password:
            raise ValueError("Password cannot be empty")
        salt = bcrypt.gensalt(rounds=PasswordService.ROUNDS)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        if not password or not password_hash:
            return False
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), password_hash.encode("utf-8")
            )
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        if len(password) < PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
        if len(password) > PASSWORD_MAX_LENGTH:
            return False, f"Password must be at most {PASSWORD_MAX_LENGTH} characters"
        if not re.search(r"[a-z]", password):
            return False, "Password must contain a lowercase letter"
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain an uppercase letter"
        if not re.search(r"\d", password):
            return False, "Password must contain a digit"
        if not re.search(r"[@$!%*?&]", password):
            return False, "Password must contain a special character (@$!%*?&)"
        return True, "Password is strong"
