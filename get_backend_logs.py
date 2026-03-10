import urllib.request
import json
try:
    req = urllib.request.Request("http://localhost:8000/health")
    with urllib.request.urlopen(req) as response:
        print("Backend is up")
except Exception as e:
    print(f"Backend not responding: {e}")
