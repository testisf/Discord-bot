import os

class BotConfig:
    """Configuration settings for the Discord bot"""
    
    # Bot settings
    BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("BOT_TOKEN", "")
    
    # Command settings
    MAX_PAD_NUMBER = 9
    MIN_PAD_NUMBER = 1
    
    # Ticket settings
    TICKET_CATEGORY_NAME = "Tickets"
    TICKET_CHANNEL_PREFIX = "ticket-"
    
    # Colors for embeds
    COLORS = {
        'success': 0x00ff00,
        'error': 0xff0000,
        'warning': 0xffaa00,
        'info': 0x0099ff,
        'primary': 0x7289da
    }
    
    # Emoji settings
    EMOJIS = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️',
        'ticket': '🎫',
        'training': '🏋️',
        'tryout': '🏃',
        'pad': '🎯'
    }
    
    @classmethod
    def validate_config(cls):
        """Validate configuration settings"""
        if not cls.BOT_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
        
        return True
