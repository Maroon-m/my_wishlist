# import os
# import json
# import psycopg2

# BACKUP_PATH = os.getenv("BACKUP_PATH", "last_backup.json")
# DATABASE_URL = os.getenv("DATABASE_URL")

# conn = psycopg2.connect(DATABASE_URL)
# cur = conn.cursor()

# with open(BACKUP_PATH, encoding="utf-8") as f:
#     data = json.load(f)

# for table_name in ["gifts", "reserves"]:
#     columns = data[table_name]["columns"]
#     rows = data[table_name]["rows"]

#     # Очищаем таблицу
#     cur.execute(f"DELETE FROM {table_name};")

#     # Вставляем строки
#     placeholders = ', '.join(['%s'] * len(columns))
#     col_names = ', '.join(columns)
#     for row in rows:
#         cur.execute(f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})", row)

# conn.commit()
# cur.close()
# conn.close()
# print("Восстановление завершено успешно")
