import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")

from unittest.mock import MagicMock
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()

sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))
from sqlalchemy import text
from apps.backend.database import engine

async def main():
    async with engine.connect() as conn:
        # Check if user 1 exists, create if not
        res = await conn.execute(text("SELECT id FROM \"user\" WHERE id = 1"))
        user_id = res.scalar()
        if not user_id:
            await conn.execute(text("INSERT INTO \"user\" (id, email) VALUES (1, 'test@example.com')"))
            
        # Create a test row
        res = await conn.execute(text("INSERT INTO row (title, status, user_id) VALUES ('Ice Cream', 'sourcing', 1) RETURNING id"))
        row_id = res.scalar()
        
        # Insert a bid with image for the row
        await conn.execute(text("""
            INSERT INTO bid (row_id, item_title, price, image_url, source) 
            VALUES (:row_id, 'Ben & Jerry''s Chocolate Chip Cookie Dough', 5.99, 'https://example.com/ice-cream.jpg', 'vendor_directory')
        """), {"row_id": row_id})
        
        # Insert a pop swap
        await conn.execute(text("""
            INSERT INTO pop_swap (category, swap_product_name, swap_product_image, provider, savings_cents) 
            VALUES ('grocery', 'Store Brand Cookie Dough', 'https://example.com/store-brand.jpg', 'manual', 200)
        """))
        
        await conn.commit()
        print(f"Created test row {row_id} with deal and swap")

asyncio.run(main())
