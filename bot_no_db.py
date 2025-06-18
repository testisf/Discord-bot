#!/usr/bin/env python3
"""
Discord bot with database-free operation for free hosting services.
This version runs entirely in memory to avoid database connection issues.
"""

import discord
from discord.ext import commands
import asyncio
import logging
import os
from datetime import datetime
from config import BotConfig
from aiohttp import web
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        # In-memory storage
        self.guild_data = {}
        self.active_tickets = {}  # Store active tickets {channel_id: user_id}

    async def setup_hook(self):
        """Called when the bot is starting up"""
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    async def on_ready(self):
        """Called when bot is ready"""
        if self.user:
            logger.info(f"{self.user.display_name}#{self.user.discriminator} has connected to Discord!")
        logger.info(f"Bot is in {len(self.guilds)} guilds")
        
        # Add persistent views for tickets
        self.add_view(TicketView())
        self.add_view(TicketCloseView())
        logger.info("Persistent views added successfully")

    async def on_guild_join(self, guild):
        """Called when bot joins a new guild"""
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
        # Initialize guild data
        if guild.id not in self.guild_data:
            self.guild_data[guild.id] = {
                'permissions': {},
                'ticket_roles': set(),
                'active_tickets': set(),
                'pad_sessions': {}
            }

    def is_server_owner(self, interaction: discord.Interaction) -> bool:
        """Check if user is the server owner"""
        return interaction.user.id == interaction.guild.owner_id

    async def owner_check(self, interaction: discord.Interaction) -> bool:
        """Owner check with error response"""
        if not self.is_server_owner(interaction):
            await interaction.response.send_message(
                f"{BotConfig.EMOJIS['error']} Only the server owner can use this command.",
                ephemeral=True
            )
            return False
        return True

# Initialize bot
bot = SimpleDiscordBot()

@bot.tree.command(name="test", description="Test if the bot is working")
async def test_command(interaction: discord.Interaction):
    """Simple test command to verify bot functionality"""
    embed = discord.Embed(
        title="✅ Bot is Working!",
        description="The Discord bot is running successfully without database dependencies.",
        color=BotConfig.COLORS['success']
    )
    embed.add_field(
        name="Status", 
        value="All systems operational", 
        inline=False
    )
    embed.add_field(
        name="Server", 
        value=interaction.guild.name, 
        inline=True
    )
    embed.add_field(
        name="Members", 
        value=str(interaction.guild.member_count), 
        inline=True
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="info", description="Get bot information")
async def info_command(interaction: discord.Interaction):
    """Display bot information"""
    embed = discord.Embed(
        title="🤖 Bot Information",
        description="Discord Bot running in memory-only mode",
        color=BotConfig.COLORS['info']
    )
    embed.add_field(
        name="Version", 
        value="1.0.0 (No Database)", 
        inline=True
    )
    embed.add_field(
        name="Servers", 
        value=str(len(bot.guilds)), 
        inline=True
    )
    embed.add_field(
        name="Mode", 
        value="Memory-only (Free hosting compatible)", 
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Check bot latency")
async def ping_command(interaction: discord.Interaction):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot latency: {latency}ms",
        color=BotConfig.COLORS['success']
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="verify", description="Verify your Roblox account (simplified version)")
async def verify_command(interaction: discord.Interaction, roblox_username: str, user: discord.Member = None):
    """Simplified verify command for no-database mode"""
    target_user = user or interaction.user
    
    embed = discord.Embed(
        title="🔍 Roblox Verification",
        description="This is a simplified verification system running without database storage.",
        color=BotConfig.COLORS['info']
    )
    embed.add_field(
        name="User", 
        value=target_user.mention, 
        inline=True
    )
    embed.add_field(
        name="Roblox Username", 
        value=roblox_username, 
        inline=True
    )
    embed.add_field(
        name="Status", 
        value="⚠️ Database verification unavailable in no-DB mode", 
        inline=False
    )
    embed.add_field(
        name="Note", 
        value="For full verification features, ensure database connection is available.", 
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Ticket System Classes
class TicketView(discord.ui.View):
    """View for ticket creation button"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.success,
        emoji="🎫",
        custom_id="create_ticket"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle ticket creation button click"""
        await create_ticket_channel(interaction)

class TicketCloseView(discord.ui.View):
    """View for ticket closing button"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="close_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle ticket close button click"""
        await close_ticket_channel(interaction)

async def create_ticket_channel(interaction: discord.Interaction):
    """Create a new ticket channel"""
    try:
        guild = interaction.guild
        user = interaction.user
        
        # Check if user already has a ticket
        existing_ticket = None
        for channel_id, ticket_user_id in bot.active_tickets.items():
            if ticket_user_id == user.id:
                channel = guild.get_channel(channel_id)
                if channel:
                    existing_ticket = channel
                    break
        
        if existing_ticket:
            embed = discord.Embed(
                title="❌ Ticket Already Exists",
                description=f"You already have an open ticket: {existing_ticket.mention}",
                color=BotConfig.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get or create tickets category
        category = None
        for cat in guild.categories:
            if cat.name.lower() == "tickets":
                category = cat
                break
        
        if not category:
            category = await guild.create_category("Tickets")
        
        # Create ticket channel
        channel_name = f"ticket-{user.name}".lower()
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Add staff roles if they exist
        for role in guild.roles:
            if any(staff_name in role.name.lower() for staff_name in ['staff', 'admin', 'mod', 'support']):
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )
        
        # Store ticket in memory
        bot.active_tickets[ticket_channel.id] = user.id
        
        # Send welcome message
        embed = discord.Embed(
            title="🎫 Ticket Created",
            description=f"Hello {user.mention}! Thank you for creating a ticket.\n\nPlease describe your issue and a staff member will assist you shortly.",
            color=BotConfig.COLORS['success']
        )
        embed.set_footer(text=f"Ticket created by {user.display_name}")
        
        close_view = TicketCloseView()
        await ticket_channel.send(embed=embed, view=close_view)
        
        # Respond to interaction
        success_embed = discord.Embed(
            title="✅ Ticket Created",
            description=f"Your ticket has been created: {ticket_channel.mention}",
            color=BotConfig.COLORS['success']
        )
        await interaction.response.send_message(embed=success_embed, ephemeral=True)
        
        logger.info(f"Ticket created: {ticket_channel.name} for {user.name}")
        
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while creating your ticket. Please try again later.",
            color=BotConfig.COLORS['error']
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def close_ticket_channel(interaction: discord.Interaction):
    """Close a ticket channel"""
    try:
        channel = interaction.channel
        
        # Check if this is a ticket channel
        if channel.id not in bot.active_tickets:
            embed = discord.Embed(
                title="❌ Not a Ticket",
                description="This command can only be used in ticket channels.",
                color=BotConfig.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get ticket owner
        ticket_owner_id = bot.active_tickets[channel.id]
        ticket_owner = interaction.guild.get_member(ticket_owner_id)
        
        # Check permissions - only allow ticket owner or members with manage_channels
        user_can_close = (interaction.user.id == ticket_owner_id)
        if hasattr(interaction.user, 'guild_permissions'):
            user_can_close = user_can_close or interaction.user.guild_permissions.manage_channels
        
        if not user_can_close:
            embed = discord.Embed(
                title="❌ No Permission",
                description="Only the ticket owner or staff can close this ticket.",
                color=BotConfig.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Send closing message
        embed = discord.Embed(
            title="🔒 Ticket Closing",
            description=f"This ticket is being closed by {interaction.user.mention}.\n\nThe channel will be deleted in 5 seconds.",
            color=BotConfig.COLORS['warning']
        )
        await interaction.response.send_message(embed=embed)
        
        # Remove from active tickets
        del bot.active_tickets[channel.id]
        
        # Wait and delete channel
        await asyncio.sleep(5)
        await channel.delete(reason=f"Ticket closed by {interaction.user.name}")
        
        logger.info(f"Ticket closed: {channel.name} by {interaction.user.name}")
        
    except Exception as e:
        logger.error(f"Error closing ticket: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while closing the ticket.",
            color=BotConfig.COLORS['error']
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="sendticket", description="Send ticket creation message")
@discord.app_commands.describe(channel="Channel to send the ticket message to")
async def sendticket(interaction: discord.Interaction, channel: discord.TextChannel = None):
    """Send ticket creation message with button"""
    # Check if user has manage_channels permission
    has_permission = False
    if hasattr(interaction.user, 'guild_permissions'):
        has_permission = interaction.user.guild_permissions.manage_channels
    
    if not has_permission:
        embed = discord.Embed(
            title="❌ No Permission",
            description="You need the 'Manage Channels' permission to use this command.",
            color=BotConfig.COLORS['error']
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    target_channel = channel or interaction.channel
    
    embed = discord.Embed(
        title="🎫 Support Tickets",
        description="Need help? Click the button below to create a support ticket!\n\nOur staff team will assist you as soon as possible.",
        color=BotConfig.COLORS['primary']
    )
    embed.add_field(
        name="How it works:",
        value="• Click 'Create Ticket'\n• A private channel will be created\n• Describe your issue\n• Wait for staff assistance",
        inline=False
    )
    embed.set_footer(text="Support System • Click the button below")
    
    view = TicketView()
    await target_channel.send(embed=embed, view=view)
    
    success_embed = discord.Embed(
        title="✅ Ticket Message Sent",
        description=f"Ticket creation message sent to {target_channel.mention}",
        color=BotConfig.COLORS['success']
    )
    await interaction.response.send_message(embed=success_embed, ephemeral=True)

async def on_application_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Handle application command errors"""
    logger.error(f"Command error: {error}")
    
    if interaction.response.is_done():
        await interaction.followup.send(
            f"{BotConfig.EMOJIS['error']} An error occurred while processing the command.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"{BotConfig.EMOJIS['error']} An error occurred while processing the command.",
            ephemeral=True
        )

bot.tree.on_error = on_application_command_error

async def health_check(request):
    """Simple health check endpoint for Render"""
    return web.Response(text="OK", status=200)

async def status_endpoint(request):
    """Status endpoint showing bot information"""
    status = {
        "bot_name": bot.user.display_name if bot.user else "Not connected",
        "guilds": len(bot.guilds) if bot.guilds else 0,
        "status": "connected" if bot.is_ready() else "connecting",
        "mode": "memory-only"
    }
    return web.json_response(status)

async def start_web_server():
    """Start a simple web server for Render compatibility"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/status', status_endpoint)
    
    # Render uses PORT environment variable, default to 10000 for Render/Railway
    port = int(os.getenv('PORT', 10000))
    logger.info(f"Starting web server on 0.0.0.0:{port}")
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"Web server started on 0.0.0.0:{port}")
    
    # Keep the web server running indefinitely
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await runner.cleanup()

async def main():
    """Main function to run both bot and web server"""
    # Validate configuration
    BotConfig.validate_config()
    
    # Get bot token
    token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("BOT_TOKEN", "")
    if not token:
        logger.error("No Discord bot token found in environment variables")
        return
    
    # Start web server in background
    web_server_task = asyncio.create_task(start_web_server())
    
    # Start bot
    try:
        bot_task = asyncio.create_task(bot.start(token))
        
        # Run both concurrently
        await asyncio.gather(web_server_task, bot_task)
    except Exception as e:
        logger.error(f"Failed to start services: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")