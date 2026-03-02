import sys, os, asyncio

sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

path = "apps/backend/models/bids.py"
with open(path, "r") as f:
    content = f.read()

# Make Vector an Any generic or strings when mock is active
import re
# We just want to fix the error in the models for development without vector db if needed.
# But actually the issue is that Vendor class fields that are Vector cause issues with Select(*).
# Let's check how many places use Vendor.
