
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import asyncpg
from decimal import Decimal

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

# Local DB
DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5435/shopping_agent"

async def dump_vendors():
    print(f"Connecting to {DATABASE_URL}...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        rows = await conn.fetch("SELECT * FROM vendor")
        print(f"Fetched {len(rows)} vendors.")
        
        vendors = []
        for row in rows:
            vendor = dict(row)
            # Convert types for JSON
            for k, v in vendor.items():
                if isinstance(v, datetime):
                    vendor[k] = v.isoformat()
                elif isinstance(v, Decimal):
                    vendor[k] = float(v)
                elif k == 'embedding' and v is not None:
                    # asyncpg returns a string for vector type usually, or maybe a list if configured?
                    # Let's check type
                    if isinstance(v, str):
                        try:
                            vendor[k] = json.loads(v)
                        except (json.JSONDecodeError, ValueError):
                            # It might be a raw string "[1,2,3]"
                            vendor[k] = [float(x) for x in v.strip("[]").split(",")]
            vendors.append(vendor)
            
        out_path = Path(__file__).parent.parent / "data/vendors_prod_dump.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out_path, "w") as f:
            json.dump(vendors, f)
            
        print(f"✅ Exported {len(vendors)} vendors to {out_path}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(dump_vendors())
