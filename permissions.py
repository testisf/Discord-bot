from typing import Set
import logging
from database import db_manager
from models import UserPermission, Guild
from sqlalchemy import and_

logger = logging.getLogger(__name__)

class PermissionManager:
    """Manages user permissions for bot commands"""
    
    def __init__(self):
        # Initialize database
        db_manager.initialize()
    
    def initialize_guild(self, guild_id: int, guild_name: str = None):
        """Initialize permission data for a guild"""
        with db_manager.get_session() as session:
            # Check if guild exists, if not create it
            guild = session.query(Guild).filter_by(id=guild_id).first()
            if not guild:
                guild = Guild(id=guild_id, name=guild_name)
                session.add(guild)
                logger.info(f"Initialized guild {guild_id} in database")
    
    def add_permission(self, guild_id: int, user_id: int, permission_type: str):
        """Add permission for a user"""
        with db_manager.get_session() as session:
            # Check if permission already exists
            existing = session.query(UserPermission).filter(
                and_(
                    UserPermission.guild_id == guild_id,
                    UserPermission.user_id == user_id,
                    UserPermission.permission_type == permission_type
                )
            ).first()
            
            if not existing:
                permission = UserPermission(
                    guild_id=guild_id,
                    user_id=user_id,
                    permission_type=permission_type
                )
                session.add(permission)
                logger.info(f"Added {permission_type} permission for user {user_id} in guild {guild_id}")
    
    def remove_permission(self, guild_id: int, user_id: int, permission_type: str):
        """Remove permission for a user"""
        with db_manager.get_session() as session:
            permission = session.query(UserPermission).filter(
                and_(
                    UserPermission.guild_id == guild_id,
                    UserPermission.user_id == user_id,
                    UserPermission.permission_type == permission_type
                )
            ).first()
            
            if permission:
                session.delete(permission)
                logger.info(f"Removed {permission_type} permission for user {user_id} in guild {guild_id}")
    
    def has_permission(self, guild_id: int, user_id: int, permission_type: str) -> bool:
        """Check if user has specific permission"""
        with db_manager.get_session() as session:
            permission = session.query(UserPermission).filter(
                and_(
                    UserPermission.guild_id == guild_id,
                    UserPermission.user_id == user_id,
                    UserPermission.permission_type == permission_type
                )
            ).first()
            
            return permission is not None
    
    def get_user_permissions(self, guild_id: int, user_id: int) -> Set[str]:
        """Get all permissions for a user"""
        with db_manager.get_session() as session:
            permissions = session.query(UserPermission).filter(
                and_(
                    UserPermission.guild_id == guild_id,
                    UserPermission.user_id == user_id
                )
            ).all()
            
            return {perm.permission_type for perm in permissions}
    
    def get_users_with_permission(self, guild_id: int, permission_type: str) -> Set[int]:
        """Get all users with a specific permission"""
        with db_manager.get_session() as session:
            permissions = session.query(UserPermission).filter(
                and_(
                    UserPermission.guild_id == guild_id,
                    UserPermission.permission_type == permission_type
                )
            ).all()
            
            return {perm.user_id for perm in permissions}
    
    def clear_guild_permissions(self, guild_id: int):
        """Clear all permissions for a guild"""
        with db_manager.get_session() as session:
            permissions = session.query(UserPermission).filter(
                UserPermission.guild_id == guild_id
            ).all()
            
            for permission in permissions:
                session.delete(permission)
            
            logger.info(f"Cleared all permissions for guild {guild_id}")
    
    def clear_user_permissions(self, guild_id: int, user_id: int):
        """Clear all permissions for a user in a guild"""
        with db_manager.get_session() as session:
            permissions = session.query(UserPermission).filter(
                and_(
                    UserPermission.guild_id == guild_id,
                    UserPermission.user_id == user_id
                )
            ).all()
            
            for permission in permissions:
                session.delete(permission)
            
            logger.info(f"Cleared all permissions for user {user_id} in guild {guild_id}")
