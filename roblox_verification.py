import aiohttp
import asyncio
import random
import string
import logging
import discord
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from database import db_manager
from models import RobloxVerification as RobloxVerificationModel, PendingVerification
from sqlalchemy import and_

logger = logging.getLogger(__name__)

class VerificationView(discord.ui.View):
    """View for Roblox verification button"""
    
    def __init__(self, roblox_verification, user_id: int, timeout=None):  # No timeout by default
        super().__init__(timeout=timeout)
        self.roblox_verification = roblox_verification
        self.user_id = user_id
    
    @discord.ui.button(label='Verify', style=discord.ButtonStyle.green, emoji='✅', custom_id='verify_roblox')
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle verification button click"""
        # Only allow the user who started verification to click the button
        if interaction.user.id != self.user_id:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="Only the user being verified can click this button.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if user has pending verification
        pending = self.roblox_verification.get_pending_verification(self.user_id)
        if not pending:
            embed = discord.Embed(
                title="❌ No Pending Verification",
                description="This verification has expired or was already completed.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Defer response as API calls might take time
        await interaction.response.defer(ephemeral=True)
        
        # Attempt to complete verification
        success, error_message = await self.roblox_verification.complete_verification(self.user_id)
        
        if success:
            verified_data = self.roblox_verification.get_verified_user(pending['guild_id'], self.user_id)
            
            # Update roles and nickname based on group membership
            guild = interaction.guild
            member = guild.get_member(self.user_id) if guild else None
            
            if member:
                update_result = await self.roblox_verification.update_user_roles_and_nickname(
                    guild, member, verified_data['roblox_id'], verified_data['roblox_username']
                )
                
                if update_result['success']:
                    embed = discord.Embed(
                        title="✅ Verification Complete",
                        description=(
                            f"**User:** <@{self.user_id}>\n"
                            f"**Roblox Username:** {verified_data['roblox_username']}\n"
                            f"**Roblox ID:** {verified_data['roblox_id']}\n"
                            f"**Group Status:** {'Member' if update_result['is_member'] else 'Not a member'}\n"
                            f"**Rank:** {update_result.get('rank_name', 'Civilian')}\n"
                            f"**Nickname:** {update_result['new_nickname']}\n"
                            f"**Role:** {update_result.get('assigned_role', 'None')}\n\n"
                            f"Verification successful! You can now remove the code from your Roblox profile."
                        ),
                        color=0x00ff00
                    )
                else:
                    embed = discord.Embed(
                        title="✅ Verification Complete",
                        description=(
                            f"**User:** <@{self.user_id}>\n"
                            f"**Roblox Username:** {verified_data['roblox_username']}\n"
                            f"**Roblox ID:** {verified_data['roblox_id']}\n\n"
                            f"Verification successful, but there was an issue updating roles: {update_result.get('error', 'Unknown error')}\n"
                            f"Use `/update` command to try again."
                        ),
                        color=0xffaa00
                    )
            else:
                embed = discord.Embed(
                    title="✅ Verification Complete",
                    description=(
                        f"**User:** <@{self.user_id}>\n"
                        f"**Roblox Username:** {verified_data['roblox_username']}\n"
                        f"**Roblox ID:** {verified_data['roblox_id']}\n\n"
                        f"Verification successful! You can now remove the code from your Roblox profile."
                    ),
                    color=0x00ff00
                )
            
            embed.set_footer(text=f"Verified by {interaction.user.display_name}")
            
            # Disable the button after successful verification
            button.disabled = True
            button.label = "Verified"
            await interaction.edit_original_response(view=self)
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Completed verification for user {self.user_id} with Roblox username {verified_data['roblox_username']}")
        else:
            # Get the verification code from pending data
            verification_code = pending.get('verification_code', 'UNKNOWN')
            embed = discord.Embed(
                title="❌ Verification Failed",
                description=f"**Error:** {error_message}\n\nMake sure the verification code `{verification_code}` is in your Roblox profile description.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def on_timeout(self):
        """Handle view timeout"""
        pass

class RobloxVerification:
    """Handles Roblox verification process using the Roblox API"""
    
    def __init__(self):
        # Initialize database
        db_manager.initialize()
        
        # CBA Group ID from the provided URL
        self.CBA_GROUP_ID = 11925205
        
        # NATO rank mapping for CBA group ranks
        self.RANK_MAPPING = {
            # Enlisted ranks
            "Recruit": "RCT",
            "Private": "PTE", 
            "Lance Corporal": "LCP",
            "Corporal": "CPL",
            "Sergeant": "SGT",
            "Staff Sergeant": "SSG",
            "Warrant Officer Class 2": "WO2",
            "Warrant Officer Class 1": "WO1",
            
            # Officer ranks
            "Second Lieutenant": "2LT",
            "Lieutenant": "LT",
            "Captain": "CPT",
            "Major": "MAJ",
            "Lieutenant Colonel": "LTC",
            "Colonel": "COL",
            "Brigadier": "BRG",
            "Major General": "MG",
            "Lieutenant General": "LG",
            "General": "GEN",
            
            # Special ranks
            "Field Marshal": "FM"
        }
    
    def generate_verification_code(self) -> str:
        """Generate a random 8-character verification code"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    async def get_roblox_user_id(self, username: str) -> Optional[int]:
        """Get Roblox user ID from username using the Roblox API"""
        try:
            async with aiohttp.ClientSession() as session:
                # Use Roblox's users API to get user ID from username
                url = "https://users.roblox.com/v1/usernames/users"
                data = {
                    "usernames": [username],
                    "excludeBannedUsers": True
                }
                
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('data') and len(result['data']) > 0:
                            return result['data'][0]['id']
                    return None
        except Exception as e:
            logger.error(f"Error fetching Roblox user ID for {username}: {e}")
            return None
    
    async def get_roblox_profile_description(self, user_id: int) -> Optional[str]:
        """Get Roblox user's profile description"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://users.roblox.com/v1/users/{user_id}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('description', '')
                    return None
        except Exception as e:
            logger.error(f"Error fetching Roblox profile description for user {user_id}: {e}")
            return None
    
    async def get_user_group_membership(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's membership information for the CBA group"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        groups = result.get('data', [])
                        
                        # Find CBA group membership
                        for group in groups:
                            if group.get('group', {}).get('id') == self.CBA_GROUP_ID:
                                return {
                                    'is_member': True,
                                    'rank_name': group.get('role', {}).get('name', 'Unknown'),
                                    'rank_id': group.get('role', {}).get('rank', 0)
                                }
                        
                        # User is not a member of the group
                        return {'is_member': False, 'rank_name': None, 'rank_id': 0}
                    return None
        except Exception as e:
            logger.error(f"Error fetching group membership for user {user_id}: {e}")
            return None

    def get_nato_rank_prefix(self, rank_name: str = None) -> str:
        """Get NATO rank prefix for a given rank name"""
        if not rank_name or rank_name == "Unknown":
            return "CIV"
        
        nato_rank = self.RANK_MAPPING.get(rank_name)
        return nato_rank if nato_rank else "CIV"

    async def verify_code_in_description(self, roblox_username: str, verification_code: str) -> Tuple[bool, Optional[int]]:
        """Check if verification code exists in user's Roblox profile description"""
        # Get user ID from username
        user_id = await self.get_roblox_user_id(roblox_username)
        if not user_id:
            return False, None
        
        # Get profile description
        description = await self.get_roblox_profile_description(user_id)
        if not description:
            return False, user_id
        
        # Check if verification code is in description
        return verification_code in description, user_id
    
    def start_verification(self, discord_user_id: int, roblox_username: str, guild_id: int) -> str:
        """Start verification process and return the verification code"""
        code = self.generate_verification_code()
        
        with db_manager.get_session() as session:
            # Remove any existing pending verification for this user
            existing = session.query(PendingVerification).filter_by(discord_user_id=discord_user_id).first()
            if existing:
                session.delete(existing)
                session.commit()  # Ensure deletion is committed before inserting
            
            # Create new pending verification
            pending = PendingVerification(
                discord_user_id=discord_user_id,
                guild_id=guild_id,
                roblox_username=roblox_username,
                verification_code=code,
                expires_at=datetime.utcnow() + timedelta(minutes=30)
            )
            session.add(pending)
            session.commit()  # Commit the new record
        
        return code
    
    async def complete_verification(self, discord_user_id: int) -> Tuple[bool, Optional[str]]:
        """Complete verification by checking if code is in Roblox profile"""
        with db_manager.get_session() as session:
            # Get pending verification
            pending = session.query(PendingVerification).filter_by(discord_user_id=discord_user_id).first()
            if not pending:
                return False, "No pending verification found"
            
            # Check if expired
            if datetime.utcnow() > pending.expires_at:
                session.delete(pending)
                return False, "Verification code has expired"
            
            code = pending.verification_code
            roblox_username = pending.roblox_username
            guild_id = pending.guild_id
            
            # Check if code is in profile
            is_verified, roblox_id = await self.verify_code_in_description(roblox_username, code)
            
            if is_verified and roblox_id:
                # Remove any existing verification for this user in this guild
                existing_verification = session.query(RobloxVerificationModel).filter(
                    and_(
                        RobloxVerificationModel.guild_id == guild_id,
                        RobloxVerificationModel.discord_user_id == discord_user_id
                    )
                ).first()
                if existing_verification:
                    existing_verification.is_active = False
                
                # Create new verification record
                verification = RobloxVerificationModel(
                    guild_id=guild_id,
                    discord_user_id=discord_user_id,
                    roblox_username=roblox_username,
                    roblox_id=roblox_id,
                    verified_at=datetime.utcnow()
                )
                session.add(verification)
                
                # Remove pending verification
                session.delete(pending)
                return True, None
            else:
                if roblox_id is None:
                    return False, f"Roblox user '{roblox_username}' not found"
                else:
                    return False, f"Verification code '{code}' not found in profile description"
    
    def get_verified_user(self, guild_id: int, discord_user_id: int) -> Optional[Dict[str, Any]]:
        """Get verified user data"""
        with db_manager.get_session() as session:
            verification = session.query(RobloxVerificationModel).filter(
                and_(
                    RobloxVerificationModel.guild_id == guild_id,
                    RobloxVerificationModel.discord_user_id == discord_user_id,
                    RobloxVerificationModel.is_active == True
                )
            ).first()
            
            if verification:
                return {
                    'roblox_username': verification.roblox_username,
                    'roblox_id': verification.roblox_id,
                    'verified_at': verification.verified_at.timestamp()
                }
            return None
    
    def get_pending_verification(self, discord_user_id: int) -> Optional[Dict[str, Any]]:
        """Get pending verification data"""
        with db_manager.get_session() as session:
            pending = session.query(PendingVerification).filter_by(discord_user_id=discord_user_id).first()
            
            if pending:
                return {
                    'verification_code': pending.verification_code,
                    'code': pending.verification_code,
                    'roblox_username': pending.roblox_username,
                    'guild_id': pending.guild_id,
                    'expires_at': pending.expires_at
                }
            return None
    
    def cancel_verification(self, discord_user_id: int) -> bool:
        """Cancel pending verification"""
        with db_manager.get_session() as session:
            pending = session.query(PendingVerification).filter_by(discord_user_id=discord_user_id).first()
            if pending:
                session.delete(pending)
                return True
            return False

    async def update_user_roles_and_nickname(self, guild: discord.Guild, member: discord.Member, roblox_id: int, roblox_username: str) -> Dict[str, Any]:
        """Update Discord user's roles and nickname based on their Roblox group membership"""
        try:
            # Get group membership
            membership = await self.get_user_group_membership(roblox_id)
            if not membership:
                return {
                    'success': False,
                    'error': 'Could not fetch group membership information'
                }

            is_member = membership['is_member']
            rank_name = membership.get('rank_name')
            
            # Get NATO rank prefix
            rank_prefix = self.get_nato_rank_prefix(rank_name)
            
            # Set nickname with rank prefix
            new_nickname = f"[{rank_prefix}] {roblox_username}"
            
            logger.info(f"Attempting to update user {member.display_name} - Rank: {rank_name}, Prefix: {rank_prefix}, Nickname: {new_nickname}")
            
            try:
                await member.edit(nick=new_nickname)
                nickname_updated = True
            except discord.Forbidden:
                nickname_updated = False
            except discord.HTTPException:
                nickname_updated = False

            # Find or create Discord role matching the Roblox rank
            role_updated = False
            assigned_role = None
            
            if is_member and rank_name:
                # Look for existing role with the rank name
                existing_role = discord.utils.get(guild.roles, name=rank_name)
                
                if not existing_role:
                    # Create the role if it doesn't exist
                    try:
                        existing_role = await guild.create_role(
                            name=rank_name,
                            reason=f"Auto-created for CBA rank: {rank_name}"
                        )
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException:
                        pass
                
                if existing_role:
                    # Remove all other CBA rank roles first
                    cba_roles = [role for role in member.roles if role.name in self.RANK_MAPPING.keys()]
                    civilian_role = discord.utils.get(guild.roles, name="Civilian")
                    if civilian_role:
                        cba_roles.append(civilian_role)
                    
                    try:
                        await member.remove_roles(*cba_roles, reason="Updating CBA rank")
                        await member.add_roles(existing_role, reason=f"Assigned CBA rank: {rank_name}")
                        role_updated = True
                        assigned_role = rank_name
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException:
                        pass
            else:
                # User is not in group - assign Civilian role
                civilian_role = discord.utils.get(guild.roles, name="Civilian")
                
                if not civilian_role:
                    # Create Civilian role if it doesn't exist
                    try:
                        civilian_role = await guild.create_role(
                            name="Civilian",
                            reason="Auto-created for non-CBA members"
                        )
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException:
                        pass
                
                if civilian_role:
                    # Remove all CBA rank roles
                    cba_roles = [role for role in member.roles if role.name in self.RANK_MAPPING.keys()]
                    
                    try:
                        await member.remove_roles(*cba_roles, reason="User not in CBA group")
                        await member.add_roles(civilian_role, reason="Assigned Civilian status")
                        role_updated = True
                        assigned_role = "Civilian"
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException:
                        pass

            return {
                'success': True,
                'is_member': is_member,
                'rank_name': rank_name,
                'rank_prefix': rank_prefix,
                'nickname_updated': nickname_updated,
                'role_updated': role_updated,
                'assigned_role': assigned_role,
                'new_nickname': new_nickname
            }

        except Exception as e:
            logger.error(f"Error updating roles and nickname for {member.display_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }