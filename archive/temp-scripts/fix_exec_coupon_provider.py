import os

path = "apps/backend/services/coupon_provider.py"
with open(path, "r") as f:
    content = f.read()

content = content.replace("result = await session.exec(stmt)", "result = await session.execute(stmt)")
content = content.replace("swaps = result.all()", "swaps = result.scalars().all()")

with open(path, "w") as f:
    f.write(content)
