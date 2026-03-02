import sys, os, asyncio
sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

from sqlalchemy import select
from apps.backend.models.bids import Vendor

stmt = select(Vendor)
print(stmt)
