# CBA Discord Bot

A comprehensive Discord bot for military roleplay servers with verification, ticket system, and member management.

## Features

- **Roblox Verification System**: Links Discord users to Roblox accounts with automatic role assignment
- **Ticket System**: Persistent ticket creation and management
- **Training/Tryout Management**: Pad booking system for military activities  
- **Member Counter**: Live server statistics display
- **Rules System**: Advanced embedded rules messages
- **Permission Management**: Role-based command access

## Commands

- `/verify` - Start Roblox verification process
- `/addrole` - Add roles to ticket access (Owner only)
- `/sendticket` - Send ticket creation message (Owner only)
- `/tryout` - Start tryout session
- `/training` - Start training session
- `/allowusers` - Manage user permissions (Owner only)
- `/update` - Update user roles from Roblox group
- `/reverify` - Re-verify user with new Roblox account
- `/memberstats` - Update member counter (Owner only)
- `/rules` - Send server rules message (Owner only)

## Deployment on Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python bot.py`
5. Add environment variables:
   - `DISCORD_BOT_TOKEN` - Your Discord bot token
   - `DATABASE_URL` - PostgreSQL database URL

## Environment Variables Required

- `DISCORD_BOT_TOKEN` - Discord bot token from Discord Developer Portal
- `DATABASE_URL` - PostgreSQL database connection string

## Database Schema

The bot uses PostgreSQL with the following tables:
- `guilds` - Server information
- `user_permissions` - Command permissions
- `ticket_roles` - Ticket access roles
- `active_pad_sessions` - Training/tryout sessions
- `active_tickets` - Open ticket channels
- `roblox_verifications` - User verification data
- `pending_verifications` - Pending verification codes

## Support

For issues or questions, contact the server administrators.