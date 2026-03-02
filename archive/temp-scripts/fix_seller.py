import os

path = "apps/backend/routes/seller.py"
with open(path, "r") as f:
    content = f.read()

content = content.replace("result = await session.exec(", "result = await session.execute(")
content = content.replace("merchant = result.first()", "merchant = result.scalar_one_or_none()")

with open(path, "w") as f:
    f.write(content)
