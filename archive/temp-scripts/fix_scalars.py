import os
import re

files_to_fix = [
    "apps/backend/routes/rows.py",
    "apps/backend/routes/rows_search.py",
    "apps/backend/routes/public_vendors.py",
    "apps/backend/routes/shares.py",
    "apps/backend/routes/seller.py",
    "apps/backend/routes/search_enriched.py",
    "apps/backend/routes/projects.py",
    "apps/backend/routes/stripe_connect.py",
    "apps/backend/routes/pop_swaps.py",
    "apps/backend/services/outreach_monitor.py",
    "apps/backend/services/outreach_service.py",
    "apps/backend/services/notify.py",
    "apps/backend/dependencies.py"
]

for file_path in files_to_fix:
    if not os.path.exists(file_path):
        continue
    with open(file_path, "r") as f:
        content = f.read()

    # The previous global replace from exec() to execute() broke .first() and .all() 
    # because execute() returns a Result object instead of scalars. 
    # Let's add .scalar_one_or_none() or .scalars().first() / .scalars().all() 
    # We will just change them back to exec() because sqlmodel's AsyncSession DOES have an exec method!
    # The error "AsyncSession has no attribute exec" was actually because it was a pure SQLAlchemy AsyncSession, not SQLModel's.
    
    # Actually wait, `database.py` imports `from sqlmodel.ext.asyncio.session import AsyncSession`. 
    # This DOES have `exec()`.
    
    content = content.replace("session.execute(", "session.exec(")
    
    with open(file_path, "w") as f:
        f.write(content)
