import requests

url = "https://frontend-production-1306.up.railway.app/api/bugs"
data = {
    "notes": "Test bug from CLI",
    "severity": "low",
    "category": "ui",
    "includeDiagnostics": "false"
}

response = requests.post(url, data=data)
print(response.status_code)
print(response.text)
