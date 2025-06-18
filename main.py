#!/usr/bin/env python3
"""
Main entry point for the Discord bot.
This file serves as a compatibility layer for deployment platforms
that expect a main.py file.
"""

if __name__ == "__main__":
    # Import and run the full bot with database support
    import asyncio
    from bot import main
    asyncio.run(main())