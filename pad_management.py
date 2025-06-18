import discord
from discord.ext import commands
from typing import Dict, Set, Optional
import asyncio
import logging
from datetime import datetime, timedelta
from config import BotConfig

logger = logging.getLogger(__name__)

class PadManager:
    """Manages training and tryout pad sessions"""
    
    def __init__(self, bot):
        self.bot = bot
        # Structure: {guild_id: {pad_number: {type: str, user_id: int, starts: int, start_time: datetime}}}
        self.active_sessions: Dict[int, Dict[int, Dict[str, any]]] = {}
    
    def initialize_guild(self, guild_id: int):
        """Initialize pad data for a guild"""
        if guild_id not in self.active_sessions:
            self.active_sessions[guild_id] = {}
            logger.info(f"Initialized pad management for guild {guild_id}")
    
    def is_pad_available(self, guild_id: int, pad_number: int) -> bool:
        """Check if a pad is available"""
        self.initialize_guild(guild_id)
        return pad_number not in self.active_sessions[guild_id]
    
    def get_pad_info(self, guild_id: int, pad_number: int) -> Optional[Dict[str, any]]:
        """Get information about a pad session"""
        self.initialize_guild(guild_id)
        return self.active_sessions[guild_id].get(pad_number)
    
    def start_session(self, guild_id: int, pad_number: int, session_type: str, user_id: int, starts: str):
        """Start a new session on a pad"""
        self.initialize_guild(guild_id)
        
        self.active_sessions[guild_id][pad_number] = {
            'type': session_type,
            'user_id': user_id,
            'starts': starts,
            'start_time': datetime.utcnow()
        }
        
        logger.info(f"Started {session_type} session on pad {pad_number} for user {user_id} in guild {guild_id}")
    
    def end_session(self, guild_id: int, pad_number: int):
        """End a session on a pad"""
        self.initialize_guild(guild_id)
        
        if pad_number in self.active_sessions[guild_id]:
            session_info = self.active_sessions[guild_id][pad_number]
            del self.active_sessions[guild_id][pad_number]
            logger.info(f"Ended {session_info['type']} session on pad {pad_number} in guild {guild_id}")
            return session_info
        
        return None
    
    def get_active_sessions(self, guild_id: int) -> Dict[int, Dict[str, any]]:
        """Get all active sessions in a guild"""
        self.initialize_guild(guild_id)
        return self.active_sessions[guild_id].copy()
    
    def get_user_sessions(self, guild_id: int, user_id: int) -> Dict[int, Dict[str, any]]:
        """Get all active sessions for a specific user"""
        self.initialize_guild(guild_id)
        
        user_sessions = {}
        for pad_number, session_info in self.active_sessions[guild_id].items():
            if session_info['user_id'] == user_id:
                user_sessions[pad_number] = session_info
        
        return user_sessions
    
    async def start_enhanced_tryout(self, interaction: discord.Interaction, tryout_type: str, starts: str, description: str):
        """Start an enhanced tryout session with detailed information"""
        guild_id = interaction.guild.id
        
        # Get user's Roblox verification data
        from roblox_verification import RobloxVerification
        roblox_verifier = RobloxVerification()
        verified_user = roblox_verifier.get_verified_user(guild_id, interaction.user.id)
        
        # Create enhanced embed
        embed = discord.Embed(
            title=f"🏃 **{tryout_type.upper()} - TRYOUT SESSION**",
            description=f"🎯 **Session Details**\n{description}",
            color=0x00ff41,  # Bright green
            timestamp=datetime.utcnow()
        )
        
        # Add session information
        embed.add_field(
            name="👤 **Host**", 
            value=f"{interaction.user.mention}\n*{interaction.user.display_name}*", 
            inline=True
        )
        embed.add_field(
            name="⏰ **Starts**", 
            value=f"```{starts}```", 
            inline=True
        )
        embed.add_field(
            name="📋 **Type**", 
            value=f"```{tryout_type}```", 
            inline=True
        )
        
        # Add Roblox information if verified
        if verified_user:
            roblox_username = verified_user['roblox_username']
            roblox_id = verified_user['roblox_id']
            
            # Get Roblox avatar URL
            avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={roblox_id}&width=420&height=420&format=png"
            embed.set_thumbnail(url=avatar_url)
            
            embed.add_field(
                name="🎮 **Roblox Profile**",
                value=f"[{roblox_username}](https://www.roblox.com/users/{roblox_id}/profile)",
                inline=True
            )
        else:
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        # Add decorative elements
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value="**📢 All interested candidates should be ready and present!**",
            inline=False
        )
        
        embed.set_footer(
            text=f"Hosted by {interaction.user.display_name} • {interaction.guild.name}",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        await interaction.response.send_message(embed=embed)

    async def start_tryout(self, interaction: discord.Interaction, pad_number: int, starts: str):
        """Start a tryout session"""
        guild_id = interaction.guild.id
        user = interaction.user
        
        # Validate starts (must not be empty)
        if not starts or not starts.strip():
            embed = discord.Embed(
                title="❌ Invalid Information",
                description="Please provide information about the tryout session.",
                color=BotConfig.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if pad is available
        if not self.is_pad_available(guild_id, pad_number):
            pad_info = self.get_pad_info(guild_id, pad_number)
            session_user = interaction.guild.get_member(pad_info['user_id'])
            
            embed = discord.Embed(
                title="❌ Pad Unavailable",
                description=(
                    f"Pad {pad_number} is currently in use.\n"
                    f"**Session Type:** {pad_info['type'].title()}\n"
                    f"**User:** {session_user.mention if session_user else 'Unknown'}\n"
                    f"**Starts:** {pad_info['starts']}\n"
                    f"**Started:** <t:{int(pad_info['start_time'].timestamp())}:R>"
                ),
                color=BotConfig.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if user already has a session
        user_sessions = self.get_user_sessions(guild_id, user.id)
        if user_sessions:
            pad_numbers = list(user_sessions.keys())
            embed = discord.Embed(
                title="❌ Session Already Active",
                description=f"You already have an active session on pad {pad_numbers[0]}.",
                color=BotConfig.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Start the session
        self.start_session(guild_id, pad_number, 'tryout', user.id, starts)
        
        # Create session embed
        embed = discord.Embed(
            title=f"🏃 Tryout Session Started - Pad {pad_number}",
            description=(
                f"**User:** {user.mention}\n"
                f"**Starts:** {starts}\n"
                f"**Started:** <t:{int(datetime.utcnow().timestamp())}:R>\n\n"
                f"Good luck with your tryout!"
            ),
            color=BotConfig.COLORS['info']
        )
        embed.set_footer(text=f"Started by {user.display_name}")
        
        # Create end session view
        view = EndSessionView(self, pad_number, user.id)
        
        await interaction.response.send_message(embed=embed, view=view)
        
        # Log the session start
        logger.info(f"Tryout session started on pad {pad_number} by {user.name} in guild {interaction.guild.name}")
    
    async def start_enhanced_training(self, interaction: discord.Interaction, training_type: str, starts: str, description: str):
        """Start an enhanced training session with detailed information"""
        guild_id = interaction.guild.id
        
        # Get user's Roblox verification data
        from roblox_verification import RobloxVerification
        roblox_verifier = RobloxVerification()
        verified_user = roblox_verifier.get_verified_user(guild_id, interaction.user.id)
        
        # Create enhanced embed
        embed = discord.Embed(
            title=f"🏋️ **{training_type.upper()} - TRAINING SESSION**",
            description=f"📚 **Training Overview**\n{description}",
            color=0x0099ff,  # Bright blue
            timestamp=datetime.utcnow()
        )
        
        # Add session information
        embed.add_field(
            name="👨‍🏫 **Instructor**", 
            value=f"{interaction.user.mention}\n*{interaction.user.display_name}*", 
            inline=True
        )
        embed.add_field(
            name="⏰ **Starts**", 
            value=f"```{starts}```", 
            inline=True
        )
        embed.add_field(
            name="📖 **Type**", 
            value=f"```{training_type}```", 
            inline=True
        )
        
        # Add Roblox information if verified
        if verified_user:
            roblox_username = verified_user['roblox_username']
            roblox_id = verified_user['roblox_id']
            
            # Get Roblox avatar URL
            avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={roblox_id}&width=420&height=420&format=png"
            embed.set_thumbnail(url=avatar_url)
            
            embed.add_field(
                name="🎮 **Roblox Profile**",
                value=f"[{roblox_username}](https://www.roblox.com/users/{roblox_id}/profile)",
                inline=True
            )
        else:
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        # Add decorative elements
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value="**🎓 All personnel are encouraged to attend this training session!**",
            inline=False
        )
        
        embed.set_footer(
            text=f"Conducted by {interaction.user.display_name} • {interaction.guild.name}",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        await interaction.response.send_message(embed=embed)

    async def start_training(self, interaction: discord.Interaction, pad_number: int, starts: str):
        """Start a training session"""
        guild_id = interaction.guild.id
        user = interaction.user
        
        # Validate starts (must not be empty)
        if not starts or not starts.strip():
            embed = discord.Embed(
                title="❌ Invalid Information",
                description="Please provide information about the training session.",
                color=BotConfig.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if pad is available
        if not self.is_pad_available(guild_id, pad_number):
            pad_info = self.get_pad_info(guild_id, pad_number)
            session_user = interaction.guild.get_member(pad_info['user_id'])
            
            embed = discord.Embed(
                title="❌ Pad Unavailable",
                description=(
                    f"Pad {pad_number} is currently in use.\n"
                    f"**Session Type:** {pad_info['type'].title()}\n"
                    f"**User:** {session_user.mention if session_user else 'Unknown'}\n"
                    f"**Starts:** {pad_info['starts']}\n"
                    f"**Started:** <t:{int(pad_info['start_time'].timestamp())}:R>"
                ),
                color=BotConfig.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if user already has a session
        user_sessions = self.get_user_sessions(guild_id, user.id)
        if user_sessions:
            pad_numbers = list(user_sessions.keys())
            embed = discord.Embed(
                title="❌ Session Already Active",
                description=f"You already have an active session on pad {pad_numbers[0]}.",
                color=BotConfig.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Start the session
        self.start_session(guild_id, pad_number, 'training', user.id, starts)
        
        # Create session embed
        embed = discord.Embed(
            title=f"🏋️ Training Session Started - Pad {pad_number}",
            description=(
                f"**User:** {user.mention}\n"
                f"**Starts:** {starts}\n"
                f"**Started:** <t:{int(datetime.utcnow().timestamp())}:R>\n\n"
                f"Have a great training session!"
            ),
            color=BotConfig.COLORS['success']
        )
        embed.set_footer(text=f"Started by {user.display_name}")
        
        # Create end session view
        view = EndSessionView(self, pad_number, user.id)
        
        await interaction.response.send_message(embed=embed, view=view)
        
        # Log the session start
        logger.info(f"Training session started on pad {pad_number} by {user.name} in guild {interaction.guild.name}")

class EndSessionView(discord.ui.View):
    """View for ending pad sessions"""
    
    def __init__(self, pad_manager: PadManager, pad_number: int, session_user_id: int):
        super().__init__(timeout=7200)  # 2 hour timeout
        self.pad_manager = pad_manager
        self.pad_number = pad_number
        self.session_user_id = session_user_id
    
    @discord.ui.button(
        label="End Session",
        style=discord.ButtonStyle.danger,
        emoji="🛑",
        custom_id="end_session"
    )
    async def end_session(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle end session button click"""
        guild_id = interaction.guild.id
        user = interaction.user
        
        # Check if user can end this session (session owner or owner)
        if user.id != self.session_user_id and user.id != interaction.guild.owner_id:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="Only the session owner or server owner can end this session.",
                color=BotConfig.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # End the session
        session_info = self.pad_manager.end_session(guild_id, self.pad_number)
        
        if session_info:
            # Calculate session duration
            duration = datetime.utcnow() - session_info['start_time']
            duration_str = str(duration).split('.')[0]  # Remove microseconds
            
            embed = discord.Embed(
                title=f"🛑 Session Ended - Pad {self.pad_number}",
                description=(
                    f"**Session Type:** {session_info['type'].title()}\n"
                    f"**User:** <@{session_info['user_id']}>\n"
                    f"**Starts:** {session_info['starts']}\n"
                    f"**Duration:** {duration_str}\n\n"
                    f"Pad {self.pad_number} is now available."
                ),
                color=BotConfig.COLORS['warning']
            )
            embed.set_footer(text=f"Ended by {user.display_name}")
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
            
            logger.info(f"Session ended on pad {self.pad_number} in guild {interaction.guild.name}")
        else:
            embed = discord.Embed(
                title="❌ Session Not Found",
                description="This session appears to have already ended.",
                color=BotConfig.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def on_timeout(self):
        """Handle view timeout"""
        # Disable all buttons when the view times out
        for item in self.children:
            item.disabled = True
