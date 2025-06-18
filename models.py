from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Guild(Base):
    """Store guild information"""
    __tablename__ = 'guilds'
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(255))
    created_at = Column(DateTime, default=func.now())

class UserPermission(Base):
    """Store user permissions for different commands"""
    __tablename__ = 'user_permissions'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    permission_type = Column(String(50), nullable=False)  # 'tryout', 'training'
    created_at = Column(DateTime, default=func.now())

class TicketRole(Base):
    """Store roles allowed to access tickets"""
    __tablename__ = 'ticket_roles'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    role_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=func.now())

class ActivePadSession(Base):
    """Store active pad sessions"""
    __tablename__ = 'active_pad_sessions'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    pad_number = Column(Integer, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    session_type = Column(String(20), nullable=False)  # 'tryout' or 'training'
    starts = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())

class ActiveTicket(Base):
    """Store active ticket channels"""
    __tablename__ = 'active_tickets'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, nullable=False, unique=True)
    user_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=func.now())

class RobloxVerification(Base):
    """Store Roblox verification data"""
    __tablename__ = 'roblox_verifications'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    discord_user_id = Column(BigInteger, nullable=False)
    roblox_username = Column(String(255), nullable=False)
    roblox_id = Column(BigInteger, nullable=False)
    verified_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)

class PendingVerification(Base):
    """Store pending verification codes"""
    __tablename__ = 'pending_verifications'
    
    id = Column(Integer, primary_key=True)
    discord_user_id = Column(BigInteger, nullable=False, unique=True)
    guild_id = Column(BigInteger, nullable=False)
    roblox_username = Column(String(255), nullable=False)
    verification_code = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)