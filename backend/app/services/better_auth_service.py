"""
Better Auth integration service
Provides authentication and user management via better-auth.com
Uses Cosmos DB for local user and farm data

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
from azure.cosmos import exceptions

from app.core.config import settings
from app.db.cosmos_client import (
    get_users_container,
    get_farms_container,
    get_farm_users_container
)
from app.db.cosmos_models import User, Farm, FarmUser, UserRole

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
                    json={"token": session_token},
                    timeout=10.0
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
                    headers=self.headers,
                    timeout=10.0
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
                    headers=self.headers,
                    timeout=10.0
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
                    },
                    timeout=10.0
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
                    },
                    timeout=10.0
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
                    headers=self.headers,
                    timeout=10.0
                )
                
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error removing member: {e}")
            return False
    
    async def create_or_get_user_local(
        self,
        better_auth_user_data: Dict[str, Any]
    ) -> User:
        """
        Create or retrieve local user from Cosmos DB
        
        Args:
            better_auth_user_data: User data from better-auth.com
        
        Returns:
            Local User model instance
        """
        better_auth_id = better_auth_user_data.get("id")
        email = better_auth_user_data.get("email")
        first_name = better_auth_user_data.get("name", "").split()[0] if better_auth_user_data.get("name") else ""
        last_name = " ".join(better_auth_user_data.get("name", "").split()[1:]) if better_auth_user_data.get("name") else ""
        
        users_container = get_users_container()
        
        try:
            # Try to get existing user by email using SQL query
            query = f"SELECT * FROM users u WHERE u.email = '{email}'"
            items = list(users_container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            
            if items:
                existing_user = User.from_dict(items[0])
                # Update better_auth_id if needed
                if not existing_user.better_auth_id:
                    existing_user.better_auth_id = better_auth_id
                    # Update in Cosmos DB
                    users_container.upsert_item(existing_user.to_dict())
                return existing_user
        except exceptions.CosmosHttpResponseError as e:
            logger.warning(f"Error querying user: {e}")
        
        # Create new user
        new_user = User(
            email=email,
            better_auth_id=better_auth_id,
            first_name=first_name,
            last_name=last_name,
            is_active=True
        )
        
        # Upsert in Cosmos DB
        users_container.upsert_item(new_user.to_dict())
        logger.info(f"Created new user: {email}")
        
        return new_user
    
    async def sync_farm_membership(
        self,
        user: User,
        better_auth_orgs: list[Dict[str, Any]]
    ) -> None:
        """
        Sync better-auth.com organization membership with local farm_users collection
        
        Args:
            user: Local User instance
            better_auth_orgs: Organizations from better-auth.com API
        """
        farm_users_container = get_farm_users_container()
        
        # Map better-auth roles to local roles
        role_mapping = {
            "owner": UserRole.OWNER,
            "admin": UserRole.MANAGER,
            "member": UserRole.STAFF
        }
        
        for org in better_auth_orgs:
            org_id = org.get("id")
            better_auth_role = org.get("role", "member")
            local_role = role_mapping.get(better_auth_role, UserRole.STAFF)
            
            try:
                # Query for existing farm_user
                query = f"SELECT * FROM farm_users fu WHERE fu.user_id = '{user.id}' AND fu.farm_id = '{org_id}'"
                items = list(farm_users_container.query_items(
                    query=query,
                    enable_cross_partition_query=True
                ))
                
                if items:
                    # Update existing
                    farm_user_data = items[0]
                    farm_user_data["role"] = local_role.value
                    farm_users_container.upsert_item(farm_user_data)
                else:
                    # Create new
                    farm_user = FarmUser(
                        user_id=user.id,
                        farm_id=org_id,
                        role=local_role
                    )
                    farm_users_container.upsert_item(farm_user.to_dict())
            except exceptions.CosmosHttpResponseError as e:
                logger.error(f"Error syncing farm membership: {e}")


# Create singleton instance
better_auth_service = BetterAuthService()

