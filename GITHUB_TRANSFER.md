# GitHub Transfer Instructions

## Step 1: Prepare Local Environment

1. Install Git if not already installed
2. Open terminal/command prompt
3. Navigate to where you want to clone the project

## Step 2: Clone and Setup Repository

```bash
# Clone the existing repository (if it exists)
git clone https://github.com/testisf/Discord-bot.git
cd Discord-bot

# Or initialize new repository
git init
git remote add origin https://github.com/testisf/Discord-bot.git
```

## Step 3: Copy Project Files

Copy these files from your current Replit project to the local repository:

**Core Bot Files:**
- `bot.py` - Main bot file
- `config.py` - Configuration settings
- `database.py` - Database manager
- `models.py` - Database models
- `permissions.py` - Permission system
- `pad_management.py` - Training/tryout system
- `ticket_system.py` - Ticket management
- `roblox_verification.py` - Roblox verification
- `member_counter.py` - Member counter system

**Configuration Files:**
- `requirements_github.txt` (rename to `requirements.txt`)
- `.gitignore`
- `README.md`
- `DEPLOYMENT.md`
- `Procfile` (for Heroku)
- `render.yaml` (for Render)
- `runtime.txt` (for Heroku)

## Step 4: Create requirements.txt

Rename `requirements_github.txt` to `requirements.txt`:

```bash
mv requirements_github.txt requirements.txt
```

## Step 5: Commit and Push

```bash
# Add all files
git add .

# Commit changes
git commit -m "Initial Discord bot project transfer"

# Push to GitHub
git push -u origin main
```

## Step 6: Environment Variables

After transfer, set up these environment variables in your deployment platform:

- `DISCORD_BOT_TOKEN` - Your Discord bot token
- `DATABASE_URL` - PostgreSQL database connection string

## Files Ready for Transfer

Your project includes:
- Complete Discord bot with slash commands
- Roblox verification system with API integration
- Ticket system with persistent views
- Training/tryout pad management
- Member counter with live updates
- Permission management system
- Database models and migrations
- Deployment configurations for multiple platforms