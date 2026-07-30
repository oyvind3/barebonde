"""
Authentication service - ID-porten OAuth2 integration
"""

from datetime import datetime, timedelta
from typing import Optional
import httpx
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.models import User, RefreshToken
from app.schemas.auth import TokenPayload


class AuthService:
    """Service for handling ID-porten authentication"""
    
    def __init__(self):
        self.client_id = settings.idporten_client_id
        self.client_secret = settings.idporten_client_secret
        self.discovery_url = settings.idporten_discovery_url
        self.redirect_url = settings.idporten_redirect_url
        self.jwt_secret = settings.jwt_secret_key
        self.jwt_algorithm = settings.jwt_algorithm
    
    def get_id_porten_login_url(self) -> str:
        """
        Generate ID-porten login URL
        """
        # In production, this would use actual ID-porten OIDC discovery
        # For now, return a placeholder that demonstrates the flow
        auth_url = f"{self.discovery_url.rstrip('/')}?client_id={self.client_id}&redirect_uri={self.redirect_url}&response_type=code&scope=openid profile email"
        return auth_url
    
    async def exchange_code_for_token(self, code: str) -> dict:
        """
        Exchange authorization code for ID-porten access token
        
        Args:
            code: Authorization code from ID-porten
        
        Returns:
            Token response from ID-porten
        """
        # This is a placeholder - in production, implement actual ID-porten token exchange
        # The actual implementation would:
        # 1. Call ID-porten token endpoint
        # 2. Exchange code + client_id + client_secret for token
        # 3. Verify token signature
        
        async with httpx.AsyncClient() as client:
            # Placeholder for ID-porten token endpoint call
            response = {
                "access_token": "placeholder_token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }
        
        return response
    
    async def get_user_info(self, access_token: str) -> dict:
        """
        Get user info from ID-porten userinfo endpoint
        
        Args:
            access_token: Access token from ID-porten
        
        Returns:
            User information from ID-porten
        """
        # Placeholder for ID-porten userinfo endpoint
        # In production, this would call the actual userinfo endpoint
        # and return user data like:
        # {
        #     "sub": "unique_id_from_idporten",
        #     "email": "user@example.com",
        #     "name": "John Doe",
        #     "given_name": "John",
        #     "family_name": "Doe"
        # }
        
        user_info = {
            "sub": "12345678901",
            "email": "farmer@example.com",
            "given_name": "John",
            "family_name": "Doe",
        }
        
        return user_info
    
    async def create_or_get_user(self, db: AsyncSession, user_info: dict) -> User:
        """
        Create or retrieve user from database
        
        Args:
            db: Database session
            user_info: User information from ID-porten
        
        Returns:
            User object
        """
        id_porten_id = user_info.get("sub")
        email = user_info.get("email")
        
        # Check if user exists
        stmt = select(User).where(User.id_porten_id == id_porten_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            user = User(
                email=email,
                id_porten_id=id_porten_id,
                first_name=user_info.get("given_name"),
                last_name=user_info.get("family_name"),
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        return user
    
    def create_access_token(self, user: User, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token
        
        Args:
            user: User object
            expires_delta: Optional expiration time delta
        
        Returns:
            JWT access token
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.jwt_expire_minutes)
        
        now = datetime.utcnow()
        expire = now + expires_delta
        
        payload = {
            "sub": user.id,
            "email": user.email,
            "iat": now,
            "exp": expire,
        }
        
        encoded_jwt = jwt.encode(
            payload,
            self.jwt_secret,
            algorithm=self.jwt_algorithm
        )
        
        return encoded_jwt
    
    async def create_refresh_token(self, db: AsyncSession, user: User) -> str:
        """
        Create and store refresh token
        
        Args:
            db: Database session
            user: User object
        
        Returns:
            Refresh token string
        """
        expires_at = datetime.utcnow() + timedelta(
            days=settings.refresh_token_expire_days
        )
        
        # Generate a simple refresh token (in production, use secrets.token_urlsafe)
        token = jwt.encode(
            {"sub": user.id, "type": "refresh"},
            self.jwt_secret,
            algorithm=self.jwt_algorithm
        )
        
        refresh_token = RefreshToken(
            user_id=user.id,
            token=token,
            expires_at=expires_at,
        )
        
        db.add(refresh_token)
        await db.commit()
        
        return token
    
    async def refresh_access_token(
        self, db: AsyncSession, refresh_token: str
    ) -> tuple[User, str]:
        """
        Refresh access token using refresh token
        
        Args:
            db: Database session
            refresh_token: Refresh token string
        
        Returns:
            Tuple of (User, new_access_token)
        """
        # Verify refresh token exists and is not revoked
        stmt = select(RefreshToken).where(
            RefreshToken.token == refresh_token,
            RefreshToken.revoked == False
        )
        result = await db.execute(stmt)
        token_obj = result.scalar_one_or_none()
        
        if not token_obj or token_obj.expires_at < datetime.utcnow():
            raise ValueError("Invalid or expired refresh token")
        
        # Get user and create new access token
        user = await db.get(User, token_obj.user_id)
        new_access_token = self.create_access_token(user)
        
        return user, new_access_token
    
    async def revoke_refresh_token(self, db: AsyncSession, refresh_token: str) -> None:
        """
        Revoke a refresh token (logout)
        
        Args:
            db: Database session
            refresh_token: Refresh token string
        """
        stmt = select(RefreshToken).where(RefreshToken.token == refresh_token)
        result = await db.execute(stmt)
        token_obj = result.scalar_one_or_none()
        
        if token_obj:
            token_obj.revoked = True
            await db.commit()
    
    def verify_token(self, token: str) -> TokenPayload:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
        
        Returns:
            Token payload
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            return TokenPayload(**payload)
        except JWTError:
            raise ValueError("Invalid token")
