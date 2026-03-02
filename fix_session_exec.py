import os

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
]

for file_path in files_to_fix:
    if not os.path.exists(file_path):
        continue
    with open(file_path, "r") as f:
        content = f.read()

    # Replace .exec( with .execute( since AsyncSession does not have .exec
    if "session.exec(" in content:
        content = content.replace("session.exec(", "session.execute(")
        with open(file_path, "w") as f:
            f.write(content)

