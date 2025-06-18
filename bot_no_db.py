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

    async def setup_hook(self):
        """Called when the bot is starting up"""
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"{self.user.display_name}#{self.user.discriminator} has connected to Discord!")
        logger.info(f"Bot is in {len(self.guilds)} guilds")

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
    
    # Render uses PORT environment variable, default to 10000 for Render
    port = int(os.getenv('PORT', 10000))
    
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