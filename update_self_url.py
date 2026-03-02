import os

path = "apps/backend/routes/chat.py"
with open(path, "r") as f:
    content = f.read()

# Make the internal self-call more robust for Next.js -> FastAPI development setups
# often running at dev.popsavings.com or railway urls.
if "_SELF_BASE_URL = _get_self_base_url()" in content:
    # Instead of guessing the local port, we can just look at an explicit PUBLIC_URL or RAILWAY_URL
    replacement = """
def _get_self_base_url() -> str:
    # First respect an explicit self call URL (useful for production/railway)
    explicit_url = os.environ.get("SELF_BASE_URL")
    if explicit_url:
        return explicit_url.rstrip("/")
        
    port = os.environ.get("PORT")
    if not port:
        import sys
        args = sys.argv
        for i, arg in enumerate(args):
            if arg == "--port" and i + 1 < len(args):
                port = args[i + 1]
                break
            if arg.startswith("--port="):
                port = arg.split("=", 1)[1]
                break
    return f"http://127.0.0.1:{port or '8000'}"

_SELF_BASE_URL = _get_self_base_url()
"""
    # Replace the old implementation
    import re
    content = re.sub(r'def _get_self_base_url.*?_SELF_BASE_URL = _get_self_base_url\(\)', replacement, content, flags=re.DOTALL)
    with open(path, "w") as f:
        f.write(content)
