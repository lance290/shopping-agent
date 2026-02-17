
import json
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "apps/backend/.env")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Local DB
DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5435/shopping_agent?sslmode=disable"

def dump_vendors():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    
    with Session() as session:
        print("Fetching vendors...")
        result = session.execute(text("SELECT * FROM vendor"))
        columns = result.keys()
        
        vendors = []
        for row in result:
            row_dict = {}
            for col, val in zip(columns, row):
                if col == 'embedding' and val is not None:
                    # pgvector/sqlalchemy might return a string or object. Convert to list.
                    # If it's a string representation like '[0.1, 0.2]', parse it.
                    if isinstance(val, str):
                        try:
                            val = json.loads(val)
                        except (json.JSONDecodeError, ValueError):
                            # Fallback if it's not valid JSON
                            val = [float(x) for x in val.strip("[]").split(",")]
                    elif hasattr(val, "tolist"): # numpy
                        val = val.tolist()
                    else:
                         # Ensure it's a list (pgvector object)
                        val = list(val)
                
                # Handle dates
                if isinstance(val, datetime):
                    val = val.isoformat()
                
                row_dict[col] = val
            vendors.append(row_dict)
            
    out_path = Path(__file__).parent.parent / "data/vendors_prod_dump.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, "w") as f:
        json.dump(vendors, f, indent=None) # Compact JSON
        
    print(f"✅ Exported {len(vendors)} vendors to {out_path}")
    return out_path

if __name__ == "__main__":
    dump_vendors()
