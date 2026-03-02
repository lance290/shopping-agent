import sys, os
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")
sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

from apps.backend.models.bids import Vendor

for col in Vendor.__table__.columns:
    print(col.name, type(col), col.type)

