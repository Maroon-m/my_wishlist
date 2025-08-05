import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "https://my-wishlist.onrender.com")
ADMIN_ID = os.getenv("ADMIN_ID", "877872483")
USERNAME = os.getenv("USERNAME")
AUTH_DATE = os.getenv("AUTH_DATE")
HASH = os.getenv("HASH")

BACKUP_ROUTE = f"{BACKEND_URL}/admin/backup"
RECEIVE_ROUTE = f"{BACKEND_URL}/admin/receive_backup"

res = requests.get(BACKUP_ROUTE, params={
    "id": ADMIN_ID,
    "username": USERNAME,
    "auth_date": AUTH_DATE,
    "hash": HASH
})

if res.ok:
    backup_data = res.json()
    resp = requests.post(RECEIVE_ROUTE, params={
        "id": ADMIN_ID,
        "username": USERNAME,
        "auth_date": AUTH_DATE,
        "hash": HASH
    }, json=backup_data)
    print("Backup sent:", resp.status_code)
else:
    print("Backup failed:", res.status_code)
