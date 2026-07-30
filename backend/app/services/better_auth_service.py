"""
Better Auth integration service
Provides authentication and user management via better-auth.com

Email Configuration (Plunk):
- Sign up at https://plunk.com
- Get API keys from your project: Settings → API Keys
  * Secret API Key (sk_...) - For server-side operations (sending emails)
  * Public API Key (pk_...) - For client-side event tracking (not used in MVP)
  
- In better-auth.com dashboard → Settings → Email Provider
  * Select Plunk as email provider
  * Paste Secret API Key (sk_...)
  * Configure sender: email (hello@barebonde.no) + name (Barebonde)
  
- Plunk will send verification/password reset/invitation emails automatically
- Docs: https://docs.useplunk.com/guides/api-keys
"""

from typing import Optional, Dict, Any
import httpx
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.models import User, FarmUser, Farm

logger = logging.getLogger(__name__)


class BetterAuthService:
    """Service for interacting with better-auth.com API"""
    
    def __init__(self):
        self.api_key = settings.better_auth_api_key
        self.base_url = settings.better_auth_base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def verify_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a session token and return session data
        
        Args:
            session_token: The session token from the client
        
        Returns:
            Session data including user info if valid, None if invalid
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/sessions/verify",
                    headers=self.headers,
                    json={"token": session_token}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Session verification failed: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error verifying session: {e}")
            return None
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user details from better-auth.com
        
        Args:
            user_id: The better-auth user ID
        
        Returns:
            User data if found
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/users/{user_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"User not found: {user_id}")
                    return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    async def get_organizations(self, user_id: str) -> list[Dict[str, Any]]:
        """
        Get all organizations (farms) a user belongs to
        
        Args:
            user_id: The better-auth user ID
        
        Returns:
            List of organizations with membership details
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/users/{user_id}/organizations",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return response.json().get("organizations", [])
                else:
                    logger.warning(f"Could not fetch organizations for user: {user_id}")
                    return []
        except Exception as e:
            logger.error(f"Error getting organizations: {e}")
            return []
    
    async def create_organization(
        self, 
        user_id: str, 
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new organization (farm) and add user as owner
        
        Args:
            user_id: The better-auth user ID (will be owner)
            name: Organization name (farm name)
            metadata: Optional additional metadata (e.g., org_number)
        
        Returns:
            Organization data if created
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/organizations",
                    headers=self.headers,
                    json={
                        "name": name,
                        "metadata": metadata or {},
                        "owner_id": user_id
                    }
                )
                
                if response.status_code == 201:
                    return response.json()
                else:
                    logger.error(f"Failed to create organization: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error creating organization: {e}")
            return None
    
    async def invite_member(
        self,
        organization_id: str,
        email: str,
        role: str = "member"
    ) -> Optional[Dict[str, Any]]:
        """
        Invite a user to an organization
        
        Args:
            organization_id: The organization ID (farm ID in better-auth)
            email: Email of user to invite
            role: Role in organization (member, admin, owner)
        
        Returns:
            Invitation data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/organizations/{organization_id}/invitations",
                    headers=self.headers,
                    json={
                        "email": email,
                        "role": role
                    }
                )
                
                if response.status_code == 201:
                    return response.json()
                else:
                    logger.error(f"Failed to invite member: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error inviting member: {e}")
            return None
    
    async def remove_member(
        self,
        organization_id: str,
        user_id: str
    ) -> bool:
        """
        Remove a user from an organization
        
        Args:
            organization_id: The organization ID
            user_id: The better-auth user ID to remove
        
        Returns:
            True if removed, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/organizations/{organization_id}/members/{user_id}",
                    headers=self.headers
                )
                
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error removing member: {e}")
            return False
    
    async def create_or_get_user_local(
        self,
        db: AsyncSession,
        better_auth_user_data: Dict[str, Any]
    ) -> User:
        """
        Create or retrieve local user from database
        
        Args:
            db: Database session
            better_auth_user_data: User data from better-auth.com
        
        Returns:
            Local User model instance
        """
        better_auth_id = better_auth_user_data.get("id")
        email = better_auth_user_data.get("email")
        first_name = better_auth_user_data.get("name", "").split()[0] if better_auth_user_data.get("name") else ""
        last_name = " ".join(better_auth_user_data.get("name", "").split()[1:]) if better_auth_user_data.get("name") else ""
        
        # Try to get existing user
        stmt = select(User).where(User.email == email)
        existing_user = await db.scalar(stmt)
        
        if existing_user:
            # Update better_auth_id if needed
            if not existing_user.better_auth_id:
                existing_user.better_auth_id = better_auth_id
            return existing_user
        
        # Create new user
        new_user = User(
            email=email,
            better_auth_id=better_auth_id,
            first_name=first_name,
            last_name=last_name,
            is_active=True
        )
        db.add(new_user)
        await db.flush()
        
        return new_user
    
    async def sync_farm_membership(
        self,
        db: AsyncSession,
        user: User,
        better_auth_orgs: list[Dict[str, Any]]
    ) -> None:
        """
        Sync better-auth.com organization membership with local farm_users table
        
        Args:
            db: Database session
            user: Local User instance
            better_auth_orgs: Organizations from better-auth.com API
        """
        # Map better-auth roles to local roles
        role_mapping = {
            "owner": "owner",
            "admin": "manager",
            "member": "staff"
        }
        
        for org in better_auth_orgs:
            org_id = org.get("id")
            better_auth_role = org.get("role", "member")
            local_role = role_mapping.get(better_auth_role, "staff")
            
            # Try to find corresponding farm by org_id stored in metadata
            # For now, assuming 1:1 mapping - org_id == farm_id (will need adjustment)
            stmt = select(FarmUser).where(
                FarmUser.user_id == user.id,
                FarmUser.farm_id == int(org_id)
            )
            farm_user = await db.scalar(stmt)
            
            if not farm_user:
                # Create farm_user if it doesn't exist
                farm_user = FarmUser(
                    user_id=user.id,
                    farm_id=int(org_id),
                    role=local_role
                )
                db.add(farm_user)
            else:
                # Update role if different
                if farm_user.role != local_role:
                    farm_user.role = local_role
        
        await db.flush()


# Create singleton instance
better_auth_service = BetterAuthService()
