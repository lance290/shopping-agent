import requests
import time

url = "https://frontend-production-1306.up.railway.app/api/bugs"
data = {
    "notes": "Test bug to verify GitHub token on Railway",
    "severity": "low",
    "category": "ui",
    "includeDiagnostics": "false"
}

print("Submitting test bug...")
response = requests.post(url, data=data)
print(f"Status: {response.status_code}")
if response.status_code == 201:
    print("Success! Check GitHub repository to see if the issue was created.")
else:
    print(f"Error: {response.text}")
