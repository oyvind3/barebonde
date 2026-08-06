"""Password hashing and verification using passlib/bcrypt."""

from __future__ import annotations

from passlib import context


# Create a passlib context with bcrypt
pwd_context = context.CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


class PasswordService:
    """Secure password hashing and verification using passlib."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt with automatic salt generation.
        
        Args:
            password: The plain text password to hash
            
        Returns:
            The hashed password as a string
        """
        if not password or len(password) < 8:
            raise ValueError("Passordet må være minst 8 tegn langt.")
        if len(password) > 72:
            raise ValueError("Passordet kan ikke være lengre enn 72 tegn.")
            
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash.
        
        Args:
            password: The plain text password to verify
            password_hash: The stored hash to verify against
            
        Returns:
            True if the password matches, False otherwise
        """
        if not password or not password_hash:
            return False
        try:
            return pwd_context.verify(password, password_hash)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def needs_rehash(password_hash: str) -> bool:
        """Check if a password hash needs to be rehashed with updated parameters.
        
        Args:
            password_hash: The stored hash to check
            
        Returns:
            True if rehashing is recommended, False otherwise
        """
        if not password_hash:
            return True
        try:
            return pwd_context.needs_rehash(password_hash)
        except (ValueError, TypeError):
            return True
