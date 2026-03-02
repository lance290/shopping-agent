import os
import re

path = "apps/backend/tests/test_pop_chat.py"
if os.path.exists(path):
    with open(path, "r") as f:
        content = f.read()

    # We renamed _stream_search to _trigger_search_local in pop_chat.py
    # Update the test patch path
    content = content.replace("routes.pop_chat._stream_search", "routes.pop_chat._trigger_search_local")

    with open(path, "w") as f:
        f.write(content)
