import os

paths = [
    "apps/backend/routes/search_enriched.py",
    "apps/backend/routes/seller.py",
    "apps/backend/routes/shares.py",
    "apps/backend/routes/stripe_connect.py"
]

for path in paths:
    with open(path, "r") as f:
        content = f.read()

    # The most common pattern
    content = content.replace("result = await session.exec(", "result = await session.execute(")
    
    # In shares.py there are direct select calls
    content = content.replace("session.exec(select(", "session.execute(select(")

    with open(path, "w") as f:
        f.write(content)

print("Fixed session.exec to session.execute in routes")
