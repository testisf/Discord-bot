# Discord Bot - replit.md

## Overview

This is a Discord bot built with Python using the discord.py library. The bot provides three main functionalities: a permission management system, a ticket creation system, and a training/tryout pad management system. The bot uses in-memory storage for session data and is designed to be lightweight and easy to deploy.

## System Architecture

### Architecture Pattern
- **Monolithic Architecture**: Single Python application with modular components
- **Event-Driven**: Uses Discord.py's event system and command handling
- **In-Memory Storage**: All data is stored in memory using Python dictionaries
- **Stateless**: No persistent database, data is lost on restart

### Core Technologies
- **Python 3.11**: Main programming language
- **discord.py 2.5.2+**: Discord API wrapper for bot functionality
- **asyncio**: Asynchronous programming for handling Discord events
- **logging**: Built-in Python logging for monitoring and debugging

## Key Components

### Bot Core (`bot.py`)
- Main bot class extending `commands.Bot`
- Handles initialization of all subsystems
- Manages Discord intents and command syncing
- Sets up activity status and logging

### Permission Manager (`permissions.py`)
- Manages user permissions across different guilds
- In-memory permission storage with guild isolation
- Supports adding, removing, and checking permissions
- Automatic cleanup of empty permission entries

### Ticket System (`ticket_system.py`)
- Provides ticket creation functionality with Discord UI components
- Uses persistent views for button interactions
- Supports ticket creation and closing workflows
- Designed for customer support or help desk scenarios

### Pad Management (`pad_management.py`)
- Manages training and tryout pad sessions (numbered 1-9)
- Tracks active sessions with user, type, and timing information
- Prevents double-booking of pads
- Supports session start and end operations

### Configuration (`config.py`)
- Centralized configuration management
- Environment variable handling for sensitive data
- Color and emoji definitions for consistent UI
- Validation methods for required settings

## Data Flow

### Permission Flow
1. User requests permission-based action
2. PermissionManager checks user permissions for guild
3. Action is allowed or denied based on permission status
4. Permissions can be modified by authorized users

### Ticket Flow
1. User clicks "Create Ticket" button
2. TicketSystem creates new ticket channel
3. User interacts within ticket channel
4. Authorized user can close ticket via "Close Ticket" button

### Pad Management Flow
1. User requests pad for training/tryout
2. PadManager checks pad availability
3. Session is created with user, type, and timing data
4. Session can be ended manually or automatically

## External Dependencies

### Required Environment Variables
- `DISCORD_BOT_TOKEN`: Discord bot authentication token

### Discord API Dependencies
- Discord gateway connection for real-time events
- Discord REST API for message and channel operations
- Discord slash command system for modern command interface

### Python Dependencies
- `discord.py>=2.5.2`: Core Discord functionality
- `asyncio`: Built-in async support
- `logging`: Built-in logging functionality
- `os`: Environment variable access
- `datetime`: Time tracking for sessions

## Deployment Strategy

### Replit Deployment
- Configured for Replit's Python 3.11 environment
- Uses Nix package manager for consistent dependencies
- Automatic dependency installation via `pip install discord.py`
- Simple shell execution for bot startup

### Environment Setup
1. Set `DISCORD_BOT_TOKEN` environment variable
2. Install discord.py dependency
3. Run `python bot.py` to start the bot

### Scaling Considerations
- Single-instance deployment (no horizontal scaling)
- In-memory storage limits to single bot instance
- Suitable for small to medium Discord servers
- Would require database integration for production scaling

## Changelog

```
Changelog:
- June 17, 2025. Initial setup
- June 17, 2025. Bot successfully deployed and running with all requested features:
  * Owner-only commands: /addrole, /allowusers
  * Ticket system: /sendticket with interactive green button
  * Pad management: /tryout and /training with permission system
  * All commands working with proper Discord slash command integration
- June 17, 2025. Updated /tryout and /training commands to accept flexible text input:
  * Changed "starts" parameter from integer to string
  * Users can now type any description instead of just numbers
  * Maintains validation to ensure input is not empty
- June 18, 2025. Added verification system with /verify and /reverify commands:
  * /verify links Discord users to Roblox usernames (owner only)
  * /reverify updates existing verifications with history tracking
  * Commands sync increased from 5 to 7 total slash commands
  * Verification data stored in memory with timestamps and verification history
- June 18, 2025. Implemented real Roblox API verification system:
  * Uses actual Roblox API to verify usernames exist
  * Requires users to add verification codes to their Roblox profile descriptions
  * Added /complete_verify command to check profile descriptions via API
  * Commands sync increased from 7 to 8 total slash commands
  * Provides secure proof of Roblox account ownership
- June 18, 2025. Enhanced verification system with interactive button:
  * /verify command now shows verification code and green "Verify" button
  * Users add code to Roblox profile, then click button to complete verification
  * Streamlined from 2-step process (/verify + /complete_verify) to single command with button
  * Button automatically checks Roblox profile and completes verification
  * More user-friendly interface with clear instructions and one-click completion
- June 18, 2025. Implemented PostgreSQL database integration:
  * Added comprehensive database models for all bot data
  * Migrated from in-memory storage to persistent database storage
  * Created 6 database tables: guilds, user_permissions, ticket_roles, active_pad_sessions, roblox_verifications, pending_verifications
  * All user permissions, verifications, and sessions now persist across bot restarts
  * Enhanced data integrity with proper database relationships and indexing
  * Bot maintains full functionality with zero data loss on restart
- June 18, 2025. Fixed ticket close button persistence issue:
  * Updated ticket system to use database instead of in-memory storage
  * Close ticket button now works indefinitely instead of failing after 2+ hours
  * Active tickets are now tracked in database with proper cleanup
  * Resolved ticket button timeout issues through persistent database storage
- June 18, 2025. Added Render hosting compatibility:
  * Integrated aiohttp web server alongside Discord bot
  * Web server binds to PORT environment variable for Render compatibility
  * Added health check endpoints (/, /health, /status) for deployment monitoring
  * Prevents port binding issues when hosting on Render or similar platforms
  * Discord bot functionality unchanged, runs concurrently with web server
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```

## Development Notes

### Database Integration
The bot now uses PostgreSQL database for persistent storage, ensuring no data loss on restarts. All data including permissions, verifications, and sessions are permanently stored with proper indexing and relationships.

### Security Considerations
- Bot token should be kept secure in environment variables
- Permission system should be enhanced with role-based access
- Consider implementing audit logging for sensitive operations

### Extension Points
- Database integration ready (modular design supports easy migration)
- Additional Discord UI components can be added
- Command system can be extended with more functionality
- Logging can be enhanced with external monitoring services