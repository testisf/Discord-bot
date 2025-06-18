import discord
import asyncio
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class MemberCounter:
    """Manages server member count display in a specific channel"""
    
    def __init__(self, bot):
        self.bot = bot
        self.target_channel_id = 1384582591516119151
        self.message_id = None
        self.update_interval = 300  # Update every 5 minutes
        self.update_task = None
    
    async def start_counter(self):
        """Start the member counter system"""
        try:
            channel = self.bot.get_channel(self.target_channel_id)
            if not channel:
                logger.error(f"Could not find channel with ID {self.target_channel_id}")
                return
            
            # Send initial message
            await self.send_member_count_message(channel)
            
            # Start periodic updates
            self.update_task = asyncio.create_task(self.update_loop())
            logger.info(f"Member counter started in channel {channel.name}")
            
        except Exception as e:
            logger.error(f"Failed to start member counter: {e}")
    
    async def update_loop(self):
        """Continuous update loop for member count"""
        while True:
            try:
                await asyncio.sleep(self.update_interval)
                channel = self.bot.get_channel(self.target_channel_id)
                if channel:
                    await self.update_member_count_message(channel)
            except Exception as e:
                logger.error(f"Error in member counter update loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def send_member_count_message(self, channel):
        """Send the initial member count message"""
        try:
            guild = channel.guild
            embed = self.create_member_count_embed(guild)
            
            # Clear previous messages in the channel (optional)
            try:
                async for message in channel.history(limit=10):
                    if message.author == self.bot.user:
                        await message.delete()
            except:
                pass  # Ignore if can't delete messages
            
            message = await channel.send(embed=embed)
            self.message_id = message.id
            logger.info(f"Sent member count message to {channel.name}")
            
        except Exception as e:
            logger.error(f"Failed to send member count message: {e}")
    
    async def update_member_count_message(self, channel):
        """Update the existing member count message"""
        try:
            if not self.message_id:
                await self.send_member_count_message(channel)
                return
            
            guild = channel.guild
            embed = self.create_member_count_embed(guild)
            
            try:
                message = await channel.fetch_message(self.message_id)
                await message.edit(embed=embed)
            except discord.NotFound:
                # Message was deleted, send a new one
                await self.send_member_count_message(channel)
            except Exception as e:
                logger.error(f"Failed to update member count message: {e}")
                
        except Exception as e:
            logger.error(f"Error updating member count: {e}")
    
    def create_member_count_embed(self, guild) -> discord.Embed:
        """Create a stylish embed for member count display"""
        # Get member statistics
        total_members = guild.member_count
        
        # Count online members more reliably
        online_members = 0
        bot_count = 0
        human_count = 0
        
        for member in guild.members:
            if member.bot:
                bot_count += 1
            else:
                human_count += 1
                
            # Check if member is online (not offline, invisible, or idle)
            if hasattr(member, 'status') and member.status in [discord.Status.online, discord.Status.dnd, discord.Status.idle]:
                online_members += 1
        
        # Fallback calculation if member iteration doesn't work
        if total_members == 0:
            total_members = guild.member_count
            human_count = total_members
            bot_count = 0
        
        # Calculate percentages
        online_percentage = (online_members / total_members * 100) if total_members > 0 else 0
        
        # Create embed with gradient-like colors
        embed = discord.Embed(
            title="🏛️ Server Statistics",
            description="**Live Member Count & Activity**",
            color=0x2F3136,
            timestamp=datetime.utcnow()
        )
        
        # Main member count field with fancy formatting
        member_display = f"""
        **📊 Total Members:** `{total_members:,}`
        **👥 Humans:** `{human_count:,}` • **🤖 Bots:** `{bot_count:,}`
        **🟢 Online:** `{online_members:,}` **({online_percentage:.1f}%)**
        """
        
        embed.add_field(
            name="🌟 Member Overview",
            value=member_display,
            inline=False
        )
        
        # Activity bar visualization
        online_bars = int(online_percentage / 10)
        offline_bars = 10 - online_bars
        activity_bar = "🟩" * online_bars + "⬛" * offline_bars
        
        embed.add_field(
            name="📈 Activity Level",
            value=f"{activity_bar}\n`{online_percentage:.1f}% Active Members`",
            inline=False
        )
        
        # Server info
        server_info = f"""
        **🏷️ Server Name:** {guild.name}
        **👑 Owner:** <@{guild.owner_id}>
        **📅 Created:** <t:{int(guild.created_at.timestamp())}:R>
        **🎭 Roles:** `{len(guild.roles):,}`
        **📝 Channels:** `{len(guild.channels):,}`
        """
        
        embed.add_field(
            name="ℹ️ Server Information",
            value=server_info,
            inline=False
        )
        
        # Add server icon as thumbnail
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Footer with update info
        embed.set_footer(
            text=f"🔄 Auto-updates every {self.update_interval//60} minutes • Last updated",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        # Add a subtle border effect with author
        embed.set_author(
            name=f"{guild.name} Live Stats",
            icon_url=guild.icon.url if guild.icon else None
        )
        
        return embed
    
    def stop_counter(self):
        """Stop the member counter system"""
        if self.update_task:
            self.update_task.cancel()
            logger.info("Member counter stopped")
    
    async def manual_update(self):
        """Manually trigger an update"""
        channel = self.bot.get_channel(self.target_channel_id)
        if channel:
            await self.update_member_count_message(channel)
            return True
        return False