"""
Cosmos DB document models
Replace SQLAlchemy models with JSON-based document structures
"""

from datetime import datetime, timezone
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
        phone_number: Optional[str] = None,
        phone_verified: bool = False,
        address: Optional[str] = None,
        onboarding_role: Optional[str] = None,
        display_name: Optional[str] = None,
        preferred_language: str = "nb",
        timezone_name: str = "Europe/Oslo",
        email_verified: bool = False,
        profile_completed: bool = False,
        terms_version: Optional[str] = None,
        terms_accepted_at: Optional[datetime] = None,
        privacy_version: Optional[str] = None,
        privacy_accepted_at: Optional[datetime] = None,
        onboarding_current_step: Optional[str] = None,
        onboarding_interests: Optional[List[str]] = None,
        onboarding_completed_at: Optional[datetime] = None,
        is_active: bool = True,
        id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        email_normalized: Optional[str] = None,
        identity_version: int = 1,
        password_hash: Optional[str] = None,
        password_set_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id or str(uuid.uuid4())
        self.user_id = user_id or self.id
        self.email = email
        self.email_normalized = email_normalized or email.strip().casefold()
        self.better_auth_id = better_auth_id  # Existing Cosmos partition key; retained for document compatibility.
        self.first_name = first_name
        self.last_name = last_name
        self.phone_number = phone_number
        self.phone_verified = phone_verified
        self.address = address
        self.onboarding_role = onboarding_role
        self.display_name = display_name or " ".join(part for part in [first_name, last_name] if part).strip()
        self.preferred_language = preferred_language
        self.timezone_name = timezone_name
        self.email_verified = email_verified
        self.profile_completed = profile_completed
        self.terms_version = terms_version
        self.terms_accepted_at = terms_accepted_at
        self.privacy_version = privacy_version
        self.privacy_accepted_at = privacy_accepted_at
        self.onboarding_current_step = onboarding_current_step
        self.onboarding_interests = onboarding_interests or []
        self.onboarding_completed_at = onboarding_completed_at
        self.is_active = is_active
        self.status = status or ("active" if is_active else "disabled")
        self.identity_version = identity_version
        self.password_hash = password_hash
        self.password_set_at = password_set_at
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or self.created_at
        self.type = "user"  # Document type discriminator
    
    def to_dict(self) -> dict:
        """Convert to Cosmos DB document"""
        return {
            "id": self.id,
            "type": self.type,
            "user_id": self.user_id,
            "status": self.status,
            "email": self.email,
            "email_normalized": self.email_normalized,
            "better_auth_id": self.better_auth_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone_number": self.phone_number,
            "phone_verified": self.phone_verified,
            "address": self.address,
            "onboarding_role": self.onboarding_role,
            "display_name": self.display_name,
            "preferred_language": self.preferred_language,
            "timezone": self.timezone_name,
            "email_verified": self.email_verified,
            "profile_completed": self.profile_completed,
            "terms_version": self.terms_version,
            "terms_accepted_at": self.terms_accepted_at.isoformat() if isinstance(self.terms_accepted_at, datetime) else self.terms_accepted_at,
            "privacy_version": self.privacy_version,
            "privacy_accepted_at": self.privacy_accepted_at.isoformat() if isinstance(self.privacy_accepted_at, datetime) else self.privacy_accepted_at,
            "onboarding_current_step": self.onboarding_current_step,
            "onboarding_interests": self.onboarding_interests,
            "onboarding_completed_at": self.onboarding_completed_at.isoformat() if isinstance(self.onboarding_completed_at, datetime) else self.onboarding_completed_at,
            "is_active": self.is_active,
            "identity_version": self.identity_version,
            "password_hash": self.password_hash,
            "password_set_at": self.password_set_at.isoformat() if isinstance(self.password_set_at, datetime) else self.password_set_at,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }
    
    @staticmethod
    def from_dict(data: dict) -> "User":
        """Create from Cosmos DB document"""
        return User(
            id=data.get("id"),
            user_id=data.get("user_id"),
            status=data.get("status"),
            email=data.get("email"),
            email_normalized=data.get("email_normalized"),
            better_auth_id=data.get("better_auth_id"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            phone_number=data.get("phone_number"),
            phone_verified=data.get("phone_verified", False),
            address=data.get("address"),
            onboarding_role=data.get("onboarding_role"),
            display_name=data.get("display_name"),
            preferred_language=data.get("preferred_language", "nb"),
            timezone_name=data.get("timezone", "Europe/Oslo"),
            email_verified=data.get("email_verified", False),
            profile_completed=data.get("profile_completed", False),
            terms_version=data.get("terms_version"),
            terms_accepted_at=datetime.fromisoformat(data.get("terms_accepted_at")) if data.get("terms_accepted_at") else None,
            privacy_version=data.get("privacy_version"),
            privacy_accepted_at=datetime.fromisoformat(data.get("privacy_accepted_at")) if data.get("privacy_accepted_at") else None,
            onboarding_current_step=data.get("onboarding_current_step"),
            onboarding_interests=data.get("onboarding_interests"),
            onboarding_completed_at=datetime.fromisoformat(data.get("onboarding_completed_at")) if data.get("onboarding_completed_at") else None,
            is_active=data.get("is_active", True),
            identity_version=data.get("identity_version", 1),
            password_hash=data.get("password_hash"),
            password_set_at=datetime.fromisoformat(data.get("password_set_at")) if data.get("password_set_at") else None,
            created_at=datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data.get("updated_at")) if data.get("updated_at") else None,
        )


class Farm:
    """Farm document in Cosmos DB"""
    
    def __init__(
        self,
        name: str,
        org_number: str,  # Partition key
        address: Optional[str] = None,
        postal_code: Optional[str] = None,
        city: Optional[str] = None,
        municipality: Optional[str] = None,
        brreg_verified: bool = False,
        organization_form: Optional[str] = None,
        industry_code: Optional[str] = None,
        primary_farm_type: Optional[str] = None,
        production_types: Optional[List[str]] = None,
        farm_size_range: Optional[str] = None,
        team_size: Optional[str] = None,
        onboarding_goals: Optional[List[str]] = None,
        billing_method: Optional[str] = None,
        billing_email: Optional[str] = None,
        farm_status: str = "active",
        created_by_user_id: Optional[str] = None,
        version: int = 1,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.org_number = org_number  # Partition key
        self.address = address or ""
        self.postal_code = postal_code or ""
        self.city = city or ""
        self.municipality = municipality or ""
        self.brreg_verified = brreg_verified
        self.organization_form = organization_form or ""
        self.industry_code = industry_code or ""
        self.primary_farm_type = primary_farm_type or ""
        self.production_types = production_types or []
        self.farm_size_range = farm_size_range or ""
        self.team_size = team_size or ""
        self.onboarding_goals = onboarding_goals or []
        self.billing_method = billing_method or ""
        self.billing_email = billing_email or ""
        self.farm_status = farm_status
        self.created_by_user_id = created_by_user_id
        self.version = version
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
            "postal_code": self.postal_code,
            "city": self.city,
            "municipality": self.municipality,
            "brreg_verified": self.brreg_verified,
            "organization_form": self.organization_form,
            "industry_code": self.industry_code,
            "primary_farm_type": self.primary_farm_type,
            "production_types": self.production_types,
            "farm_size_range": self.farm_size_range,
            "team_size": self.team_size,
            "onboarding_goals": self.onboarding_goals,
            "billing_method": self.billing_method,
            "billing_email": self.billing_email,
            "farm_status": self.farm_status,
            "created_by_user_id": self.created_by_user_id,
            "version": self.version,
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
            postal_code=data.get("postal_code"),
            city=data.get("city"),
            municipality=data.get("municipality"),
            brreg_verified=data.get("brreg_verified", False),
            organization_form=data.get("organization_form"),
            industry_code=data.get("industry_code"),
            primary_farm_type=data.get("primary_farm_type"),
            production_types=data.get("production_types"),
            farm_size_range=data.get("farm_size_range"),
            team_size=data.get("team_size"),
            onboarding_goals=data.get("onboarding_goals"),
            billing_method=data.get("billing_method"),
            billing_email=data.get("billing_email"),
            farm_status=data.get("farm_status", "active"),
            created_by_user_id=data.get("created_by_user_id"),
            version=data.get("version", 1),
            created_at=datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data.get("updated_at")) if data.get("updated_at") else None
        )


class FarmUser:
    """Farm-User association document in Cosmos DB"""

    @staticmethod
    def membership_id(farm_id: str, user_id: str) -> str:
        """Stable ID for point reads in the ``/farm_id`` partition."""
        return f"membership:{farm_id}:{user_id}"
    
    def __init__(
        self,
        user_id: str,
        farm_id: str,  # Partition key
        role: UserRole = UserRole.STAFF,
        farm_role: Optional[str] = None,
        membership_status: str = "active",
        invited_by_user_id: Optional[str] = None,
        invited_at: Optional[datetime] = None,
        accepted_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        farm_name: Optional[str] = None,
        org_number: Optional[str] = None,
        version: int = 1,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id or self.membership_id(farm_id, user_id)
        self.user_id = user_id
        self.farm_id = farm_id  # Partition key
        role_value = role.value if isinstance(role, UserRole) else str(role)
        self.farm_role = farm_role or role_value
        self.role = self.farm_role  # Legacy compatibility during lazy migration.
        self.membership_status = membership_status
        self.invited_by_user_id = invited_by_user_id
        self.invited_at = invited_at
        self.accepted_at = accepted_at or datetime.utcnow()
        self.expires_at = expires_at
        self.farm_name = farm_name or ""
        self.org_number = org_number or ""
        self.version = version
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or self.created_at
        self.type = "farm_user"  # Document type discriminator
    
    def to_dict(self) -> dict:
        """Convert to Cosmos DB document"""
        return {
            "id": self.id,
            "type": self.type,
            "user_id": self.user_id,
            "farm_id": self.farm_id,
            "farm_role": self.farm_role,
            "role": self.role,
            "membership_status": self.membership_status,
            "invited_by_user_id": self.invited_by_user_id,
            "invited_at": self.invited_at.isoformat() if isinstance(self.invited_at, datetime) else self.invited_at,
            "accepted_at": self.accepted_at.isoformat() if isinstance(self.accepted_at, datetime) else self.accepted_at,
            "expires_at": self.expires_at.isoformat() if isinstance(self.expires_at, datetime) else self.expires_at,
            "farm_name": self.farm_name,
            "org_number": self.org_number,
            "version": self.version,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }
    
    @staticmethod
    def from_dict(data: dict) -> "FarmUser":
        """Create from Cosmos DB document"""
        role_value = data.get("farm_role") or data.get("role", "staff")
        role = UserRole(role_value) if role_value in {item.value for item in UserRole} else UserRole.STAFF
        
        return FarmUser(
            id=data.get("id"),
            user_id=data.get("user_id"),
            farm_id=data.get("farm_id"),
            role=role,
            farm_role=data.get("farm_role"),
            membership_status=data.get("membership_status", "active"),
            invited_by_user_id=data.get("invited_by_user_id"),
            invited_at=datetime.fromisoformat(data.get("invited_at")) if data.get("invited_at") else None,
            accepted_at=datetime.fromisoformat(data.get("accepted_at")) if data.get("accepted_at") else None,
            expires_at=datetime.fromisoformat(data.get("expires_at")) if data.get("expires_at") else None,
            farm_name=data.get("farm_name"),
            org_number=data.get("org_number"),
            version=data.get("version", 1),
            created_at=datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data.get("updated_at")) if data.get("updated_at") else None,
        )


class Subscription:
    """The single current subscription document for a Farm tenant."""

    @staticmethod
    def subscription_id(farm_id: str) -> str:
        return f"subscription:{farm_id}"

    def __init__(
        self,
        farm_id: str,
        plan_code: str,
        plan_version: str,
        subscription_status: str = "active",
        started_at: Optional[datetime] = None,
        current_period_start: Optional[datetime] = None,
        current_period_end: Optional[datetime] = None,
        trial_ends_at: Optional[datetime] = None,
        grace_period_ends_at: Optional[datetime] = None,
        cancel_at_period_end: bool = False,
        canceled_at: Optional[datetime] = None,
        payment_provider: Optional[str] = None,
        external_customer_id: Optional[str] = None,
        external_subscription_id: Optional[str] = None,
        version: int = 1,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        timestamp = datetime.now(timezone.utc)
        self.id = id or self.subscription_id(farm_id)
        self.type = "subscription"
        self.farm_id = farm_id
        self.plan_code = plan_code
        self.plan_version = plan_version
        self.subscription_status = subscription_status
        self.started_at = started_at or timestamp
        self.current_period_start = current_period_start
        self.current_period_end = current_period_end
        self.trial_ends_at = trial_ends_at
        self.grace_period_ends_at = grace_period_ends_at
        self.cancel_at_period_end = cancel_at_period_end
        self.canceled_at = canceled_at
        self.payment_provider = payment_provider
        self.external_customer_id = external_customer_id
        self.external_subscription_id = external_subscription_id
        self.version = version
        self.created_at = created_at or timestamp
        self.updated_at = updated_at or self.created_at

    @staticmethod
    def _timestamp(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if isinstance(value, datetime) else value

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "farm_id": self.farm_id,
            "plan_code": self.plan_code,
            "plan_version": self.plan_version,
            "subscription_status": self.subscription_status,
            "started_at": self._timestamp(self.started_at),
            "current_period_start": self._timestamp(self.current_period_start),
            "current_period_end": self._timestamp(self.current_period_end),
            "trial_ends_at": self._timestamp(self.trial_ends_at),
            "grace_period_ends_at": self._timestamp(self.grace_period_ends_at),
            "cancel_at_period_end": self.cancel_at_period_end,
            "canceled_at": self._timestamp(self.canceled_at),
            "payment_provider": self.payment_provider,
            "external_customer_id": self.external_customer_id,
            "external_subscription_id": self.external_subscription_id,
            "version": self.version,
            "created_at": self._timestamp(self.created_at),
            "updated_at": self._timestamp(self.updated_at),
        }


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


class AccountingDocument:
    """Bilag document metadata for Cosmos DB."""

    def __init__(
        self,
        farm_id: str,
        file_name: str,
        content_type: str,
        blob_name: str,
        size_bytes: int,
        blob_url: Optional[str] = None,
        status: str = "mottatt",
        account_code: Optional[str] = None,
        mva_code: Optional[str] = None,
        amount: float = 0.0,
        voucher_date: Optional[str] = None,
        description: Optional[str] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id or str(uuid.uuid4())
        self.type = "voucher_document"
        self.farm_id = farm_id
        self.file_name = file_name
        self.content_type = content_type
        self.blob_name = blob_name
        self.blob_url = blob_url
        self.size_bytes = size_bytes
        self.status = status
        self.account_code = account_code
        self.mva_code = mva_code
        self.amount = amount
        self.voucher_date = voucher_date or datetime.utcnow().date().isoformat()
        self.description = description or ""
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        document = {
            "id": self.id,
            "type": self.type,
            "farm_id": self.farm_id,
            "file_name": self.file_name,
            "content_type": self.content_type,
            "blob_name": self.blob_name,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "account_code": self.account_code,
            "mva_code": self.mva_code,
            "amount": self.amount,
            "voucher_date": self.voucher_date,
            "description": self.description,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }
        # Old documents can retain this metadata, but new writes must not
        # normalize a direct Blob URL into the document schema.
        if self.blob_url:
            document["blob_url"] = self.blob_url
        return document


class AccountingTransaction:
    """Booked accounting transaction linked to voucher documents."""

    def __init__(
        self,
        farm_id: str,
        voucher_id: str,
        transaction_type: str,
        amount: float,
        account_code: str,
        category: str = "Drift",
        mva_code: Optional[str] = None,
        description: Optional[str] = None,
        voucher_date: Optional[str] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id or str(uuid.uuid4())
        self.type = "accounting_transaction"
        self.farm_id = farm_id
        self.voucher_id = voucher_id
        self.transaction_type = transaction_type
        self.amount = amount
        self.account_code = account_code
        self.category = category
        self.mva_code = mva_code
        self.description = description or ""
        self.voucher_date = voucher_date or datetime.utcnow().date().isoformat()
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "farm_id": self.farm_id,
            "voucher_id": self.voucher_id,
            "transaction_type": self.transaction_type,
            "amount": self.amount,
            "account_code": self.account_code,
            "category": self.category,
            "mva_code": self.mva_code,
            "description": self.description,
            "voucher_date": self.voucher_date,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }
