# Deployment Guide

## GitHub Setup

1. Clone or download this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables (see below)
4. Run the bot: `python bot.py`

## Environment Variables

Create a `.env` file or set these environment variables:

```
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DATABASE_URL=postgresql://username:password@host:port/database
```

## Render.com Deployment

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python main.py`
5. Add environment variables:
   - `DISCORD_BOT_TOKEN` - Your Discord bot token
   - `DATABASE_URL` - PostgreSQL database URL (optional - bot runs without database)

**Important**: The bot will automatically bind to the PORT environment variable provided by Render. The web server starts on 0.0.0.0 which is required for Render to detect the service.

## Heroku Deployment

1. Create a new Heroku app
2. Add PostgreSQL addon: `heroku addons:create heroku-postgresql:hobby-dev`
3. Set config vars: `heroku config:set DISCORD_BOT_TOKEN=your_token`
4. Deploy: `git push heroku main`

## Railway Deployment

1. Create new project on Railway
2. Connect GitHub repository
3. Add PostgreSQL database
4. Set environment variables in Railway dashboard
5. Deploy automatically on push

## Discord Bot Setup

1. Go to Discord Developer Portal
2. Create new application
3. Create bot user
4. Copy bot token to environment variables
5. Invite bot to server with Administrator permissions