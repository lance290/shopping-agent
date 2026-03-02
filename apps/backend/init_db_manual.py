import asyncio
import os
import sys

sys.path.append(os.getcwd())

from database import init_db
from models import *

async def main():
    print("Running init_db()...")
    await init_db()
    print("Done!")

asyncio.run(main())
