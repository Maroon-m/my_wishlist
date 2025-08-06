import requests
import os
import json

# URL получения бэкапа
BACKUP_URL = os.getenv("BACKUP_URL", "https://my-wishlist.onrender.com/admin/backup")

# URL, куда отправляется бэкап
RECEIVE_URL = os.getenv("BACKUP_RECEIVE_URL", "https://my-wishlist.onrender.com/admin/backup?token=supersecrettoken")

# Получить бэкап
response = requests.get(BACKUP_URL)
response.raise_for_status()
data = response.json()

# Сохраняем локально
timestamp = os.popen("date -u +%Y-%m-%dT%H-%M-%SZ").read().strip()
backup_path = f"backups/backup_{timestamp}.json"
with open(backup_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Отправить обратно
res = requests.post(RECEIVE_URL, json=data)
res.raise_for_status()
print("Backup sent to server successfully.")
