import requests
import sys

try:
    response = requests.get("http://127.0.0.1:5000/admin/index")
    print(f"Status code: {response.status_code}")
    print("Test successful!")
except Exception as e:
    print(f"Error: {str(e)}")
    sys.exit(1)
