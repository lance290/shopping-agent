import os

path = "apps/backend/routes/pop_swaps.py"
with open(path, "r") as f:
    content = f.read()

content = content.replace("result = await session.exec(", "result = await session.execute(")

with open(path, "w") as f:
    f.write(content)
