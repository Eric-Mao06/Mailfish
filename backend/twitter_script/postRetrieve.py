import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

url = "https://twitter241.p.rapidapi.com/user-tweets"

querystring = {"user":"1543018484170473476","count":"20"}

headers = {
    "x-rapidapi-key": os.getenv('RAPID_API_KEY'),
    "x-rapidapi-host": "twitter241.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())