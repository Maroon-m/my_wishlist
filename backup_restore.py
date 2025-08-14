import os, json, psycopg
from psycopg.rows import dict_row

  
BACKUP_FILE = './backups/backup.json'
DB_URL = 'postgresql://postgres:dverkavmir@db.yhabecpddlfpntjbhugb.supabase.co:5432/postgres'


def as_gift(row):
    # допуски: либо dict, либо список в порядке колонок
    if isinstance(row, dict):
        return (row["id"], row["title"], row["description"], row["link"], row["category"], bool(row.get("given", False)))
    # fallback для старых бэкапов-списков: [id,title,description,link,category,given]
    return (int(row[0]), row[1], row[2], row[3], row[4], bool(row[5]) if len(row) > 5 else False)

def as_reserve(row):
    # dict или [gift_id,tg_id,username,timestamp]
    if isinstance(row, dict):
        return (row["gift_id"], row["tg_id"], row.get("username",""), row["timestamp"])
    return (int(row[0]), int(row[1]), row[2] if len(row) > 2 else "", int(row[3]) if len(row) > 3 else 0)

def main():
    with open(BACKUP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    gifts = data.get("gifts", [])
    reserves = data.get("reserves", [])
    over = data.get("overlimit_attempts", data.get("overlimit", []))  # на случай другого ключа

    with psycopg.connect(DB_URL, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            create table if not exists gifts (
              id serial primary key,
              title text,
              description text,
              link text,
              category text,
              given boolean default false
            );""")
            cur.execute("""
            create table if not exists reserves (
              gift_id integer,
              tg_id bigint,
              username text,
              timestamp bigint
            );""")
            cur.execute("""
            create table if not exists overlimit_attempts (
              tg_id bigint,
              username text,
              timestamp bigint
            );""")

            # очищаем перед заливкой (если нужно именно восстановление)
            cur.execute("truncate table reserves;")
            cur.execute("truncate table overlimit_attempts;")
            cur.execute("truncate table gifts restart identity;")

            # gifts
            for g in gifts:
                id_, title, desc, link, cat, given = as_gift(g)
                cur.execute("""
                  insert into gifts (id, title, description, link, category, given)
                  values (%s,%s,%s,%s,%s,%s)
                  on conflict (id) do update set
                    title=excluded.title,
                    description=excluded.description,
                    link=excluded.link,
                    category=excluded.category,
                    given=excluded.given;
                """, (id_, title, desc, link, cat, given))

            # reserves
            for r in reserves:
                gift_id, tg_id, username, ts = as_reserve(r)
                cur.execute("insert into reserves (gift_id,tg_id,username,timestamp) values (%s,%s,%s,%s);",
                            (gift_id, tg_id, username or "", ts))

            # overlimit_attempts (если есть в бэкапе)
            for o in over:
                if isinstance(o, dict):
                    tg_id, username, ts = o["tg_id"], o.get("username",""), o["timestamp"]
                else:
                    tg_id, username, ts = int(o[0]), (o[1] if len(o)>1 else ""), int(o[2] if len(o)>2 else 0)
                cur.execute("insert into overlimit_attempts (tg_id,username,timestamp) values (%s,%s,%s);",
                            (tg_id, username or "", ts))

            # поправим sequence
            cur.execute("select coalesce(max(id),0) from gifts;")
            max_id = cur.fetchone()[0]
            cur.execute("select setval(pg_get_serial_sequence('gifts','id'), %s, true);", (max_id,))
        conn.commit()

if __name__ == "__main__":
    main()

