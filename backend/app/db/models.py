"""
SQLAlchemy models for Barebonde
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum


Base = declarative_base()


class UserRole(str, enum.Enum):
    """User roles in a farm"""
    OWNER = "owner"
    MANAGER = "manager"
    STAFF = "staff"


class Farm(Base):
    """
    A farm/gård - the central entity
    Represents a single agricultural business
    """
    __tablename__ = "farms"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)  # Gårdens navn
    org_number = Column(String(9), unique=True, nullable=False)  # Organisasjonsnummer
    address = Column(String(255))
    municipality = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("FarmUser", back_populates="farm", cascade="all, delete-orphan")
    properties = relationship("Property", back_populates="farm", cascade="all, delete-orphan")


class User(Base):
    """
    A user who can access one or more farms
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    better_auth_id = Column(String(255), unique=True, nullable=False)  # better-auth user ID
    first_name = Column(String(255))
    last_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    farm_users = relationship("FarmUser", back_populates="user", cascade="all, delete-orphan")


class FarmUser(Base):
    """
    Association table: User -> Farm with role
    """
    __tablename__ = "farm_users"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.STAFF)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="farm_users")
    farm = relationship("Farm", back_populates="users")


class Property(Base):
    """
    Real estate/eiendom owned by farm
    """
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    name = Column(String(255))
    area_hectares = Column(Integer)  # Areal i dekar/hectare
    gardskart_id = Column(String(255))  # Reference to Gårdskart
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    farm = relationship("Farm", back_populates="properties")


class RefreshToken(Base):
    """
    Refresh tokens for JWT authentication
    """
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(500), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
