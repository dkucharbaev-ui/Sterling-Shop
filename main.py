import sys
import os
import asyncio

# Add bot and backend to Python path
root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(root, "bot"))
sys.path.insert(0, os.path.join(root, "backend"))

from bot.main import main

if __name__ == "__main__":
    asyncio.run(main())
