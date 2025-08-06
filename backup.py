import requests
import os
import json

# Получить из переменных окружения
BACKUP_SECRET = os.getenv("BACKUP_SECRET", "supersecrettoken")
BACKEND_URL = os.getenv("BACKEND_URL", "https://my-wishlist.onrender.com")

# Маршруты
GET_URL = f"{BACKEND_URL}/admin/backup?token=supersecrettoken"
POST_URL = f"{BACKEND_URL}/admin/receive_backup?token=supersecrettoken"

# 1. Получить бэкап
response = requests.get(GET_URL)
response.raise_for_status()
data = response.json()

# 2. Сохранить локально
timestamp = os.popen("date -u +%Y-%m-%dT%H-%M-%SZ").read().strip()
backup_path = f"backups/backup_{timestamp}.json"
with open(backup_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 3. Отправить на сервер
res = requests.post(POST_URL, json=data)
res.raise_for_status()
print("Backup complete.")
