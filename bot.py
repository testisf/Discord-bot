import discord
from discord.ext import commands
import asyncio
import logging
import os
from datetime import datetime
from config import BotConfig
from permissions import PermissionManager
from ticket_system import TicketSystem
from pad_management import PadManager
from roblox_verification import RobloxVerification
from member_counter import MemberCounter
from aiohttp import web, ClientSession
import threading

# Import database manager
from database import db_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DiscordBot(commands.Bot):
    def __init__(self):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.presences = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        # Initialize managers
        self.permission_manager = PermissionManager()
        self.ticket_system = TicketSystem(self)
        self.pad_manager = PadManager(self)
        self.roblox_verification = RobloxVerification()
        self.member_counter = MemberCounter(self)
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Setup persistent views after bot is ready
        self.ticket_system.setup_views()
        
        # Start member counter
        await self.member_counter.start_counter()
        
        # Set activity status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="for tickets and training"
        )
        await self.change_presence(activity=activity)
    
    async def on_guild_join(self, guild):
        """Called when bot joins a new guild"""
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
        
        # Initialize guild data
        self.permission_manager.initialize_guild(guild.id, guild.name)
        self.ticket_system.initialize_guild(guild.id)
        self.pad_manager.initialize_guild(guild.id)
    
    def is_server_owner(self, interaction: discord.Interaction) -> bool:
        """Check if user is the server owner"""
        if interaction.guild and interaction.guild.owner_id:
            return interaction.user.id == interaction.guild.owner_id
        return False
    
    async def owner_check(self, interaction: discord.Interaction) -> bool:
        """Owner check with error response"""
        if not self.is_server_owner(interaction):
            embed = discord.Embed(
                title="❌ Access Denied",
                description="This command is restricted to the server owner only.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

# Initialize bot instance
bot = DiscordBot()

# Add slash commands
@bot.tree.command(name="addrole", description="Add a role to ticket access list (Owner only)")
@discord.app_commands.describe(role="The role to add to ticket access list")
async def addrole(interaction: discord.Interaction, role: discord.Role):
    """Add role to ticket access list"""
    if not await bot.owner_check(interaction):
        return
    
    guild_id = interaction.guild.id
    
    # Add role to ticket access
    bot.ticket_system.add_role(guild_id, role.id)
    
    embed = discord.Embed(
        title="✅ Role Added",
        description=f"Role {role.mention} has been added to the ticket access list.",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)
    logger.info(f"Role {role.name} added to ticket access in guild {interaction.guild.name}")

@bot.tree.command(name="sendticket", description="Send ticket creation message to a channel")
@discord.app_commands.describe(channel="The channel to send the ticket message to")
async def sendticket(interaction: discord.Interaction, channel: discord.TextChannel):
    """Send ticket creation message with button"""
    guild_id = interaction.guild.id
    
    # Check if user has permission (owner or has ticket role)
    if not bot.is_server_owner(interaction):
        if hasattr(interaction.user, 'roles'):
            user_roles = [role.id for role in interaction.user.roles]
            ticket_roles = bot.ticket_system.get_roles(guild_id)
            
            if not any(role_id in ticket_roles for role_id in user_roles):
                embed = discord.Embed(
                    title="❌ Access Denied", 
                    description="You don't have permission to send ticket messages.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        else:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="You don't have permission to send ticket messages.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    # Send ticket message to specified channel
    await bot.ticket_system.send_ticket_message(channel)
    
    embed = discord.Embed(
        title="✅ Ticket Message Sent",
        description=f"Ticket creation message has been sent to {channel.mention}.",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="tryout", description="Start tryout session with detailed information")
@discord.app_commands.describe(
    tryout_type="Type of tryout (e.g., 'Infantry Training', 'Officer Evaluation')",
    starts="When the tryout starts (e.g., 'in 10 minutes', '3:00 PM')",
    description="Description of the tryout requirements and details"
)
async def tryout(interaction: discord.Interaction, tryout_type: str, starts: str, description: str):
    """Start tryout session with enhanced details"""
    # Check permissions
    guild_id = interaction.guild.id
    user_id = interaction.user.id
    
    if not bot.is_owner(interaction) and not bot.permission_manager.has_permission(guild_id, user_id, 'tryout'):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="You don't have permission to use the tryout command.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Start enhanced tryout session
    await bot.pad_manager.start_enhanced_tryout(interaction, tryout_type, starts, description)

@bot.tree.command(name="training", description="Start training session with detailed information")
@discord.app_commands.describe(
    training_type="Type of training (e.g., 'Combat Training', 'Leadership Workshop')",
    starts="When the training starts (e.g., 'in 10 minutes', '3:00 PM')",
    description="Description of the training objectives and requirements"
)
async def training(interaction: discord.Interaction, training_type: str, starts: str, description: str):
    """Start training session with enhanced details"""
    # Check permissions
    guild_id = interaction.guild.id
    user_id = interaction.user.id
    
    if not bot.is_owner(interaction) and not bot.permission_manager.has_permission(guild_id, user_id, 'training'):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="You don't have permission to use the training command.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Start enhanced training session
    await bot.pad_manager.start_enhanced_training(interaction, training_type, starts, description)

@bot.tree.command(name="allowusers", description="Manage user permissions for tryout/training commands (Owner only)")
@discord.app_commands.describe(
    user="The user to modify permissions for",
    command_type="Command type to grant permission for",
    action="Whether to add or remove permission"
)
@discord.app_commands.choices(
    command_type=[
        discord.app_commands.Choice(name="tryout", value="tryout"),
        discord.app_commands.Choice(name="training", value="training"),
        discord.app_commands.Choice(name="both", value="both")
    ],
    action=[
        discord.app_commands.Choice(name="add", value="add"),
        discord.app_commands.Choice(name="remove", value="remove")
    ]
)
async def allowusers(interaction: discord.Interaction, user: discord.Member, command_type: str, action: str):
    """Manage user permissions"""
    if not await bot.owner_check(interaction):
        return
    
    guild_id = interaction.guild.id
    user_id = user.id
    
    if action == "add":
        if command_type == "both":
            bot.permission_manager.add_permission(guild_id, user_id, 'tryout')
            bot.permission_manager.add_permission(guild_id, user_id, 'training')
            description = f"Added tryout and training permissions for {user.mention}"
        else:
            bot.permission_manager.add_permission(guild_id, user_id, command_type)
            description = f"Added {command_type} permission for {user.mention}"
    else:  # remove
        if command_type == "both":
            bot.permission_manager.remove_permission(guild_id, user_id, 'tryout')
            bot.permission_manager.remove_permission(guild_id, user_id, 'training')
            description = f"Removed tryout and training permissions for {user.mention}"
        else:
            bot.permission_manager.remove_permission(guild_id, user_id, command_type)
            description = f"Removed {command_type} permission for {user.mention}"
    
    embed = discord.Embed(
        title="✅ Permissions Updated",
        description=description,
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)
    logger.info(f"Permission {action} for user {user.name} in guild {interaction.guild.name}")

@bot.tree.command(name="verify", description="Start Roblox verification process")
@discord.app_commands.describe(
    user="The Discord user to verify (leave empty to verify yourself)",
    roblox_username="The user's Roblox username"
)
async def verify(interaction: discord.Interaction, roblox_username: str, user: discord.Member = None):
    """Start Roblox verification process with profile description check"""
    # Defer response immediately to prevent timeout
    await interaction.response.defer()
    
    # Determine target user
    target_user = user if user else interaction.user
    
    # Only server owners can verify other users, but anyone can verify themselves
    if user and user.id != interaction.user.id and not bot.is_server_owner(interaction):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="Only server owners can verify other users. Use `/verify roblox_username` to verify yourself.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    guild_id = interaction.guild.id
    
    # Check if user is already verified
    existing_verification = bot.roblox_verification.get_verified_user(guild_id, target_user.id)
    if existing_verification:
        embed = discord.Embed(
            title="⚠️ Already Verified",
            description=f"{target_user.mention} is already verified as **{existing_verification['roblox_username']}**\nUse `/reverify` to update their verification.",
            color=0xffaa00
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Check if Roblox username exists
    roblox_id = await bot.roblox_verification.get_roblox_user_id(roblox_username)
    if not roblox_id:
        embed = discord.Embed(
            title="❌ User Not Found",
            description=f"Roblox user **{roblox_username}** does not exist.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Start verification process
    verification_code = bot.roblox_verification.start_verification(target_user.id, roblox_username, guild_id)
    
    # Import the VerificationView class
    from roblox_verification import VerificationView
    
    embed = discord.Embed(
        title="🔐 Roblox Verification Started",
        description=(
            f"**User:** {target_user.mention}\n"
            f"**Roblox Username:** {roblox_username}\n"
            f"**Verification Code:** `{verification_code}`\n\n"
            f"**Instructions:**\n"
            f"1. Go to your Roblox profile: https://www.roblox.com/users/{roblox_id}/profile\n"
            f"2. Edit your profile description\n"
            f"3. Add the verification code `{verification_code}` anywhere in your description\n"
            f"4. Save your profile\n"
            f"5. Click the **Verify** button below to complete verification\n\n"
            f"The code must remain in your description until verification is complete."
        ),
        color=0x0099ff
    )
    embed.set_footer(text="Verification button never expires - you can use it anytime")
    
    # Create verification view with button (no timeout)
    view = VerificationView(bot.roblox_verification, target_user.id)
    
    await interaction.followup.send(embed=embed, view=view)
    logger.info(f"Started verification for {target_user.name} with Roblox username {roblox_username} in guild {interaction.guild.name}")

@bot.tree.command(name="memberstats", description="Update member counter display")
async def memberstats(interaction: discord.Interaction):
    """Manually update the member counter display"""
    if not bot.is_server_owner(interaction):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="Only server owners can manually update member statistics.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    success = await bot.member_counter.manual_update()
    if success:
        embed = discord.Embed(
            title="✅ Member Stats Updated",
            description="The member counter display has been refreshed.",
            color=0x00ff00
        )
    else:
        embed = discord.Embed(
            title="❌ Update Failed",
            description="Could not update the member counter display.",
            color=0xff0000
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="rules", description="Send server rules message")
@discord.app_commands.describe(channel="The channel to send the rules message to")
async def rules(interaction: discord.Interaction, channel: discord.TextChannel = None):
    """Send an advanced rules message"""
    if not bot.is_server_owner(interaction):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="Only server owners can send rules messages.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    target_channel = channel if channel else interaction.channel
    
    # Create main rules embed
    embed = discord.Embed(
        title="📋 **SERVER RULES & REGULATIONS**",
        description="*Read carefully and follow all rules to maintain your membership*",
        color=0x2F3136,
        timestamp=datetime.utcnow()
    )
    
    # General Rules Section
    general_rules = """
    🔸 Respect all players – No bullying, harassment, or racism
    🔸 Follow Roblox Terms of Service – Violations = instant removal
    🔸 No exploiting, glitching, or using third-party tools
    🔸 No advertising other groups or games
    🔸 Use English in main chat channels
    """
    
    embed.add_field(
        name="📜 ━ **𝐆𝐄𝐍𝐄𝐑𝐀𝐋 𝐑𝐔𝐋𝐄𝐒** ━ 📜",
        value=general_rules,
        inline=False
    )
    
    # Military Roleplay Rules Section
    military_rules = """
    🔸 Always listen to higher ranks (Chain of Command)
    🔸 Salute Officers and follow drill commands
    🔸 No trolling, running around base, or acting immature
    🔸 Attend trainings, patrols, and parades when online
    🔸 Stay in uniform when on duty
    """
    
    embed.add_field(
        name="🎖 ━ **𝐌𝐈𝐋𝐈𝐓𝐀𝐑𝐘 𝐑𝐎𝐋𝐄𝐏𝐋𝐀𝐘 𝐑𝐔𝐋𝐄𝐒** ━ 🎖",
        value=military_rules,
        inline=False
    )
    
    # Discipline & Punishments Section
    discipline_rules = """
    🔸 Warning → Kick → Blacklist – Based on severity
    🔸 Disobeying officers may lead to demotion or removal
    🔸 Trolling during events = Instant kick
    🔸 False reporting or lying to staff is not tolerated
    """
    
    embed.add_field(
        name="🛡 ━ **𝐃𝐈𝐒𝐂𝐈𝐏𝐋𝐈𝐍𝐄 & 𝐏𝐔𝐍𝐈𝐒𝐇𝐌𝐄𝐍𝐓𝐒** ━ 🛡",
        value=discipline_rules,
        inline=False
    )
    
    # Discord Server Rules Section
    discord_rules = """
    🔸 Use channels for their purpose (e.g., #questions in help)
    🔸 Do not ping high ranks unless necessary
    🔸 No NSFW, spam, or toxic behavior
    🔸 Respect mods and server staff
    🔸 Username must be appropriate and non-offensive
    """
    
    embed.add_field(
        name="💬 ━ **𝐃𝐈𝐒𝐂𝐎𝐑𝐃 𝐒𝐄𝐑𝐕𝐄𝐑 𝐑𝐔𝐋𝐄𝐒** ━ 💬",
        value=discord_rules,
        inline=False
    )
    
    # Add footer and thumbnail
    embed.set_footer(
        text="By staying in this server, you agree to follow these rules",
        icon_url=interaction.guild.icon.url if interaction.guild.icon else None
    )
    
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    
    # Add accent line
    embed.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        value="**Thank you for being part of our community!**",
        inline=False
    )
    
    try:
        await target_channel.send(embed=embed)
        
        success_embed = discord.Embed(
            title="✅ Rules Posted",
            description=f"Server rules have been posted to {target_channel.mention}",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=success_embed, ephemeral=True)
        
    except discord.Forbidden:
        error_embed = discord.Embed(
            title="❌ Permission Error",
            description="I don't have permission to send messages in that channel.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="complete_verify", description="Complete the Roblox verification process")
@discord.app_commands.describe(user="The Discord user to complete verification for")
async def complete_verify(interaction: discord.Interaction, user: discord.Member):
    """Complete the Roblox verification by checking profile description"""
    if not await bot.owner_check(interaction):
        return
    
    # Check if user has pending verification
    pending = bot.roblox_verification.get_pending_verification(user.id)
    if not pending:
        embed = discord.Embed(
            title="❌ No Pending Verification",
            description=f"{user.mention} has no pending verification. Use `/verify` first.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Defer response as API calls might take time
    await interaction.response.defer()
    
    # Attempt to complete verification
    success, error_message = await bot.roblox_verification.complete_verification(user.id)
    
    if success:
        verified_data = bot.roblox_verification.get_verified_user(pending['guild_id'], user.id)
        embed = discord.Embed(
            title="✅ Verification Complete",
            description=(
                f"**User:** {user.mention}\n"
                f"**Roblox Username:** {verified_data['roblox_username']}\n"
                f"**Roblox ID:** {verified_data['roblox_id']}\n\n"
                f"Verification successful! You can now remove the code from your Roblox profile."
            ),
            color=0x00ff00
        )
        embed.set_footer(text=f"Verified by {interaction.user.display_name}")
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Completed verification for {user.name} with Roblox username {verified_data['roblox_username']} in guild {interaction.guild.name}")
    else:
        embed = discord.Embed(
            title="❌ Verification Failed",
            description=f"**Error:** {error_message}\n\nMake sure the verification code `{pending['code']}` is in your Roblox profile description.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="reverify", description="Update a user's Roblox verification")
@discord.app_commands.describe(
    user="The Discord user to re-verify",
    roblox_username="The user's new Roblox username"
)
async def reverify(interaction: discord.Interaction, user: discord.Member, roblox_username: str):
    """Re-verify a user with a new Roblox username"""
    if not await bot.owner_check(interaction):
        return
    
    guild_id = interaction.guild.id
    
    # Cancel any pending verification
    bot.roblox_verification.cancel_verification(user.id)
    
    # Check if Roblox username exists
    roblox_id = await bot.roblox_verification.get_roblox_user_id(roblox_username)
    if not roblox_id:
        embed = discord.Embed(
            title="❌ User Not Found",
            description=f"Roblox user **{roblox_username}** does not exist.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Start new verification process
    verification_code = bot.roblox_verification.start_verification(user.id, roblox_username, guild_id)
    
    embed = discord.Embed(
        title="🔄 Roblox Re-verification Started",
        description=(
            f"**User:** {user.mention}\n"
            f"**New Roblox Username:** {roblox_username}\n"
            f"**Verification Code:** `{verification_code}`\n\n"
            f"**Instructions:**\n"
            f"1. Go to your Roblox profile: https://www.roblox.com/users/{roblox_id}/profile\n"
            f"2. Edit your profile description\n"
            f"3. Add the verification code `{verification_code}` anywhere in your description\n"
            f"4. Save your profile\n"
            f"5. Use `/complete_verify @{user.display_name}` to complete verification\n\n"
            f"This will replace any existing verification."
        ),
        color=0x0099ff
    )
    embed.set_footer(text="Verification expires in 30 minutes")
    
    await interaction.response.send_message(embed=embed)
    logger.info(f"Started re-verification for {user.name} with Roblox username {roblox_username} in guild {interaction.guild.name}")

@bot.tree.command(name="update", description="Update your Discord roles and nickname based on current Roblox group rank")
@discord.app_commands.describe(user="The user to update (leave empty to update yourself)")
async def update(interaction: discord.Interaction, user: discord.Member = None):
    """Update user's Discord roles and nickname based on their current Roblox group membership"""
    # Determine target user
    target_user = user if user else interaction.user
    
    # Only server owners can update other users
    if user and not bot.is_server_owner(interaction):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="Only server owners can update other users. Use `/update` without mentioning a user to update yourself.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    guild_id = interaction.guild.id
    
    # Check if user is verified
    verified_data = bot.roblox_verification.get_verified_user(guild_id, target_user.id)
    if not verified_data:
        embed = discord.Embed(
            title="❌ Not Verified",
            description=f"{target_user.mention} is not verified. Use `/verify` to link a Roblox account first.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Defer response as this might take time
    await interaction.response.defer()
    
    # Get member object
    member = interaction.guild.get_member(target_user.id)
    if not member:
        embed = discord.Embed(
            title="❌ Member Not Found",
            description="Could not find the user in this server.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Update roles and nickname
    update_result = await bot.roblox_verification.update_user_roles_and_nickname(
        interaction.guild, member, verified_data['roblox_id'], verified_data['roblox_username']
    )
    
    if update_result['success']:
        embed = discord.Embed(
            title="✅ Update Complete",
            description=(
                f"**User:** {target_user.mention}\n"
                f"**Roblox Username:** {verified_data['roblox_username']}\n"
                f"**Group Status:** {'Member' if update_result['is_member'] else 'Not a member'}\n"
                f"**Rank:** {update_result.get('rank_name', 'Civilian')}\n"
                f"**Nickname:** {update_result['new_nickname']}\n"
                f"**Role:** {update_result.get('assigned_role', 'None')}\n"
                f"**Nickname Updated:** {'✅' if update_result['nickname_updated'] else '❌'}\n"
                f"**Role Updated:** {'✅' if update_result['role_updated'] else '❌'}"
            ),
            color=0x00ff00
        )
        embed.set_footer(text=f"Updated by {interaction.user.display_name}")
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Updated roles and nickname for {target_user.name} in guild {interaction.guild.name}")
    else:
        embed = discord.Embed(
            title="❌ Update Failed",
            description=(
                f"**User:** {target_user.mention}\n"
                f"**Error:** {update_result.get('error', 'Unknown error occurred')}\n\n"
                f"This could be due to missing bot permissions or API issues."
            ),
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

# Error handling
@bot.event
async def on_application_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Handle application command errors"""
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        embed = discord.Embed(
            title="⏰ Command on Cooldown",
            description=f"Please wait {error.retry_after:.2f} seconds before using this command again.",
            color=0xffaa00
        )
    elif isinstance(error, discord.app_commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Missing Permissions",
            description="You don't have the required permissions to use this command.",
            color=0xff0000
        )
    else:
        embed = discord.Embed(
            title="❌ Error",
            description="An unexpected error occurred while processing your command.",
            color=0xff0000
        )
        logger.error(f"Unhandled command error: {error}")
    
    if not interaction.response.is_done():
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send(embed=embed, ephemeral=True)

async def health_check(request):
    """Simple health check endpoint for Render"""
    return web.Response(text="Discord Bot is running!", status=200)

async def status_endpoint(request):
    """Status endpoint showing bot information"""
    if bot.is_ready():
        guild_count = len(bot.guilds)
        return web.json_response({
            "status": "online",
            "guilds": guild_count,
            "user": str(bot.user) if bot.user else "Not connected"
        })
    else:
        return web.json_response({"status": "connecting"}, status=503)

async def start_web_server():
    """Start a simple web server for Render compatibility"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/status', status_endpoint)
    
    # Get port from environment (Render sets this)
    port = int(os.getenv('PORT', 8080))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Web server started on port {port}")

async def main():
    """Main function to run both bot and web server"""
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("DISCORD_BOT_TOKEN environment variable not found!")
        exit(1)
    
    try:
        # Start web server for Render compatibility
        await start_web_server()
        
        # Start Discord bot
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("Invalid bot token provided!")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

# Run the bot
if __name__ == "__main__":
    asyncio.run(main())
