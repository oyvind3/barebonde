"""
Cosmos DB document models
Replace SQLAlchemy models with JSON-based document structures
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid


class UserRole(str, Enum):
    """User roles in a farm"""
    OWNER = "owner"
    MANAGER = "manager"
    STAFF = "staff"


class User:
    """User document in Cosmos DB"""
    
    def __init__(
        self,
        email: str,
        better_auth_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        is_active: bool = True,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.email = email
        self.better_auth_id = better_auth_id  # Partition key
        self.first_name = first_name
        self.last_name = last_name
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.type = "user"  # Document type discriminator
    
    def to_dict(self) -> dict:
        """Convert to Cosmos DB document"""
        return {
            "id": self.id,
            "type": self.type,
            "email": self.email,
            "better_auth_id": self.better_auth_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }
    
    @staticmethod
    def from_dict(data: dict) -> "User":
        """Create from Cosmos DB document"""
        return User(
            id=data.get("id"),
            email=data.get("email"),
            better_auth_id=data.get("better_auth_id"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else None
        )


class Farm:
    """Farm document in Cosmos DB"""
    
    def __init__(
        self,
        name: str,
        org_number: str,  # Partition key
        address: Optional[str] = None,
        municipality: Optional[str] = None,
        brreg_verified: bool = False,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.org_number = org_number  # Partition key
        self.address = address or ""
        self.municipality = municipality or ""
        self.brreg_verified = brreg_verified
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.type = "farm"  # Document type discriminator
    
    def to_dict(self) -> dict:
        """Convert to Cosmos DB document"""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "org_number": self.org_number,
            "address": self.address,
            "municipality": self.municipality,
            "brreg_verified": self.brreg_verified,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }
    
    @staticmethod
    def from_dict(data: dict) -> "Farm":
        """Create from Cosmos DB document"""
        return Farm(
            id=data.get("id"),
            name=data.get("name"),
            org_number=data.get("org_number"),
            address=data.get("address"),
            municipality=data.get("municipality"),
            brreg_verified=data.get("brreg_verified", False),
            created_at=datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data.get("updated_at")) if data.get("updated_at") else None
        )


class FarmUser:
    """Farm-User association document in Cosmos DB"""
    
    def __init__(
        self,
        user_id: str,
        farm_id: str,  # Partition key
        role: UserRole = UserRole.STAFF,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.user_id = user_id
        self.farm_id = farm_id  # Partition key
        self.role = role
        self.created_at = created_at or datetime.utcnow()
        self.type = "farm_user"  # Document type discriminator
    
    def to_dict(self) -> dict:
        """Convert to Cosmos DB document"""
        return {
            "id": self.id,
            "type": self.type,
            "user_id": self.user_id,
            "farm_id": self.farm_id,
            "role": self.role.value if isinstance(self.role, UserRole) else self.role,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }
    
    @staticmethod
    def from_dict(data: dict) -> "FarmUser":
        """Create from Cosmos DB document"""
        role_value = data.get("role", "staff")
        role = UserRole(role_value) if isinstance(role_value, str) else role_value
        
        return FarmUser(
            id=data.get("id"),
            user_id=data.get("user_id"),
            farm_id=data.get("farm_id"),
            role=role,
            created_at=datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else None
        )


class Property:
    """Property document in Cosmos DB"""
    
    def __init__(
        self,
        farm_id: str,  # Partition key
        name: Optional[str] = None,
        area_hectares: Optional[int] = None,
        gardskart_id: Optional[str] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.farm_id = farm_id  # Partition key
        self.name = name
        self.area_hectares = area_hectares
        self.gardskart_id = gardskart_id
        self.created_at = created_at or datetime.utcnow()
        self.type = "property"  # Document type discriminator
    
    def to_dict(self) -> dict:
        """Convert to Cosmos DB document"""
        return {
            "id": self.id,
            "type": self.type,
            "farm_id": self.farm_id,
            "name": self.name,
            "area_hectares": self.area_hectares,
            "gardskart_id": self.gardskart_id,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }
    
    @staticmethod
    def from_dict(data: dict) -> "Property":
        """Create from Cosmos DB document"""
        return Property(
            id=data.get("id"),
            farm_id=data.get("farm_id"),
            name=data.get("name"),
            area_hectares=data.get("area_hectares"),
            gardskart_id=data.get("gardskart_id"),
            created_at=datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else None
        )
