import requests
import os
import json
import sys

BACKEND_URL = os.getenv("BACKEND_URL", "https://my-wishlist.onrender.com")
BACKUP_SECRET = os.getenv("BACKUP_SECRET")

BACKUP_URL = f"{BACKEND_URL}/admin/backup?token={BACKUP_SECRET}"

# Куда сохраняем (берём из аргумента, иначе backup.json в текущей папке)
save_path = sys.argv[1] if len(sys.argv) > 1 else "backup.json"

# Получаем данные
response = requests.get(BACKUP_URL)
response.raise_for_status()
data = response.json()

# Сохраняем в файл
with open(save_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Backup saved to {save_path}")
