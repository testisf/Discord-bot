import discord
from discord.ext import commands
from typing import Set, List
import asyncio
import logging
from config import BotConfig
from database import db_manager
from models import TicketRole, Guild, ActiveTicket
from sqlalchemy import and_

logger = logging.getLogger(__name__)

class TicketView(discord.ui.View):
    """View for ticket creation button"""
    
    def __init__(self, ticket_system):
        super().__init__(timeout=None)
        self.ticket_system = ticket_system
    
    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.success,
        emoji="🎫",
        custom_id="create_ticket"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle ticket creation button click"""
        await self.ticket_system.create_ticket(interaction)

class TicketCloseView(discord.ui.View):
    """View for ticket closing button"""
    
    def __init__(self, ticket_system):
        super().__init__(timeout=None)
        self.ticket_system = ticket_system
    
    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="close_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle ticket close button click"""
        await self.ticket_system.close_ticket(interaction)

class TicketSystem:
    """Manages the ticket system functionality"""
    
    def __init__(self, bot):
        self.bot = bot
        # Initialize database
        db_manager.initialize()
        
    def setup_views(self):
        """Setup persistent views - called after bot is ready"""
        try:
            # Add persistent views
            self.bot.add_view(TicketView(self))
            self.bot.add_view(TicketCloseView(self))
            logger.info("Persistent views added successfully")
        except Exception as e:
            logger.error(f"Failed to setup views: {e}")
    
    def initialize_guild(self, guild_id: int):
        """Initialize ticket data for a guild"""
        with db_manager.get_session() as session:
            # Check if guild exists, if not create it
            guild = session.query(Guild).filter_by(id=guild_id).first()
            if not guild:
                guild = Guild(id=guild_id)
                session.add(guild)
                logger.info(f"Initialized ticket system for guild {guild_id}")
    
    def add_role(self, guild_id: int, role_id: int):
        """Add role to ticket access list"""
        with db_manager.get_session() as session:
            # Check if role already exists
            existing = session.query(TicketRole).filter(
                and_(
                    TicketRole.guild_id == guild_id,
                    TicketRole.role_id == role_id
                )
            ).first()
            
            if not existing:
                ticket_role = TicketRole(guild_id=guild_id, role_id=role_id)
                session.add(ticket_role)
                logger.info(f"Added role {role_id} to ticket access in guild {guild_id}")
    
    def remove_role(self, guild_id: int, role_id: int):
        """Remove role from ticket access list"""
        with db_manager.get_session() as session:
            ticket_role = session.query(TicketRole).filter(
                and_(
                    TicketRole.guild_id == guild_id,
                    TicketRole.role_id == role_id
                )
            ).first()
            
            if ticket_role:
                session.delete(ticket_role)
                logger.info(f"Removed role {role_id} from ticket access in guild {guild_id}")
    
    def get_roles(self, guild_id: int) -> Set[int]:
        """Get ticket access roles for a guild"""
        with db_manager.get_session() as session:
            roles = session.query(TicketRole).filter(
                TicketRole.guild_id == guild_id
            ).all()
            
            return {role.role_id for role in roles}
    
    def has_ticket_access(self, guild_id: int, member: discord.Member) -> bool:
        """Check if member has ticket access"""
        # Owner always has access
        if member.id == member.guild.owner_id:
            return True
        
        # Check if member has any of the ticket roles
        member_roles = {role.id for role in member.roles}
        ticket_roles = self.get_roles(guild_id)
        
        return bool(member_roles.intersection(ticket_roles))
    
    async def send_ticket_message(self, channel: discord.TextChannel):
        """Send ticket creation message to a channel"""
        embed = discord.Embed(
            title="🎫 Support Tickets",
            description=(
                "Need help? Click the button below to create a support ticket.\n\n"
                "Our support team will assist you as soon as possible!"
            ),
            color=BotConfig.COLORS['primary']
        )
        embed.set_footer(text="Click the green button to create a ticket")
        
        view = TicketView(self)
        await channel.send(embed=embed, view=view)
        logger.info(f"Sent ticket message to channel {channel.name} in guild {channel.guild.name}")
    
    async def create_ticket(self, interaction: discord.Interaction):
        """Create a new ticket channel"""
        try:
            guild = interaction.guild
            user = interaction.user
            
            # Check if user already has an open ticket
            with db_manager.get_session() as session:
                existing_ticket_record = session.query(ActiveTicket).filter(
                    and_(
                        ActiveTicket.guild_id == guild.id,
                        ActiveTicket.user_id == user.id
                    )
                ).first()
                
                if existing_ticket_record:
                    channel = guild.get_channel(existing_ticket_record.channel_id)
                    if channel:
                        embed = discord.Embed(
                            title="❌ Ticket Already Exists",
                            description=f"You already have an open ticket: {channel.mention}",
                            color=BotConfig.COLORS['error']
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                    else:
                        # Channel was deleted, remove from database
                        session.delete(existing_ticket_record)
                        session.commit()  # Commit the deletion
            
            # Get or create ticket category
            category = discord.utils.get(guild.categories, name=BotConfig.TICKET_CATEGORY_NAME)
            if not category:
                try:
                    category = await guild.create_category(BotConfig.TICKET_CATEGORY_NAME)
                    logger.info(f"Created ticket category in guild {guild.name}")
                except discord.Forbidden:
                    embed = discord.Embed(
                        title="❌ Permission Error",
                        description="Bot doesn't have permission to create categories.",
                        color=BotConfig.COLORS['error']
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
            
            # Create ticket channel
            channel_name = f"{BotConfig.TICKET_CHANNEL_PREFIX}{user.display_name.lower().replace(' ', '-')}"
            
            # Set up permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    read_message_history=True
                )
            }
            
            # Add ticket access roles
            ticket_roles = self.get_roles(guild.id)
            for role_id in ticket_roles:
                role = guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        read_message_history=True
                    )
            
            try:
                ticket_channel = await category.create_text_channel(
                    name=channel_name,
                    overwrites=overwrites,
                    topic=f"Ticket for {user.display_name} ({user.id})"
                )
                
                # Register ticket in database
                with db_manager.get_session() as session:
                    active_ticket = ActiveTicket(
                        guild_id=guild.id,
                        channel_id=ticket_channel.id,
                        user_id=user.id
                    )
                    session.add(active_ticket)
                
                # Send welcome message
                embed = discord.Embed(
                    title="🎫 Ticket Created",
                    description=(
                        f"Hello {user.mention}!\n\n"
                        "Thank you for creating a support ticket. Please describe your issue "
                        "and our support team will help you shortly.\n\n"
                        "Click the red button below to close this ticket when resolved."
                    ),
                    color=BotConfig.COLORS['success']
                )
                embed.set_footer(text=f"Ticket created by {user.display_name}")
                
                close_view = TicketCloseView(self)
                await ticket_channel.send(embed=embed, view=close_view)
                
                # Respond to interaction
                embed = discord.Embed(
                    title="✅ Ticket Created",
                    description=f"Your ticket has been created: {ticket_channel.mention}",
                    color=BotConfig.COLORS['success']
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                logger.info(f"Created ticket {ticket_channel.name} for user {user.name} in guild {guild.name}")
                
            except discord.Forbidden:
                embed = discord.Embed(
                    title="❌ Permission Error",
                    description="Bot doesn't have permission to create channels.",
                    color=BotConfig.COLORS['error']
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to create ticket channel.",
                    color=BotConfig.COLORS['error']
                )
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                    else:
                        await interaction.followup.send(embed=embed, ephemeral=True)
                except:
                    pass  # If we can't respond, at least log the error
                logger.error(f"Failed to create ticket: {e}")
        
        except Exception as e:
            # Handle any unexpected errors at the top level
            embed = discord.Embed(
                title="❌ Unexpected Error",
                description="An unexpected error occurred while creating the ticket.",
                color=BotConfig.COLORS['error']
            )
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass  # If we can't respond, at least log the error
            logger.error(f"Unexpected error in create_ticket: {e}")
    
    async def close_ticket(self, interaction: discord.Interaction):
        """Close a ticket channel"""
        channel = interaction.channel
        guild = interaction.guild
        user = interaction.user
        
        # Check if this is a ticket channel
        with db_manager.get_session() as session:
            active_ticket = session.query(ActiveTicket).filter(
                and_(
                    ActiveTicket.guild_id == guild.id,
                    ActiveTicket.channel_id == channel.id
                )
            ).first()
            
            if not active_ticket:
                embed = discord.Embed(
                    title="❌ Not a Ticket",
                    description="This command can only be used in ticket channels.",
                    color=BotConfig.COLORS['error']
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            ticket_owner_id = active_ticket.user_id
        
        # Check permissions (ticket owner, staff with ticket role, or owner)
        can_close = (
            user.id == ticket_owner_id or
            user.id == guild.owner_id or
            self.has_ticket_access(guild.id, user)
        )
        
        if not can_close:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="You don't have permission to close this ticket.",
                color=BotConfig.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Confirm closure
        embed = discord.Embed(
            title="🔒 Closing Ticket",
            description="This ticket will be closed in 5 seconds...",
            color=BotConfig.COLORS['warning']
        )
        await interaction.response.send_message(embed=embed)
        
        # Wait and close
        await asyncio.sleep(5)
        
        # Remove from database
        with db_manager.get_session() as session:
            active_ticket = session.query(ActiveTicket).filter(
                and_(
                    ActiveTicket.guild_id == guild.id,
                    ActiveTicket.channel_id == channel.id
                )
            ).first()
            
            if active_ticket:
                session.delete(active_ticket)
        
        try:
            await channel.delete(reason=f"Ticket closed by {user.display_name}")
            logger.info(f"Closed ticket {channel.name} in guild {guild.name}")
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="Bot doesn't have permission to delete this channel.",
                color=BotConfig.COLORS['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to close ticket: {e}")
