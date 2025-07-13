from flask import Flask, request, jsonify
import time, hmac, hashlib, os, html
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [877872483]
DATABASE_URL = os.getenv("DATABASE_URL")

def verify_telegram(data):
    check = "\n".join(f"{k}={data[k]}" for k in sorted(data) if k not in ['hash', 'gift_id'])
    secret = hashlib.sha256(BOT_TOKEN.encode()).digest()
    if hmac.new(secret, check.encode(), hashlib.sha256).hexdigest() != data['hash']:
        return False
    if time.time() - int(data.get('auth_date', 0)) > 86400:
        return False
    return True

def get_db():
    conn = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS gifts (
            id SERIAL PRIMARY KEY,
            title TEXT,
            description TEXT,
            link TEXT,
            category TEXT
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS reserves (
            gift_id INTEGER,
            tg_id BIGINT,
            username TEXT,
            timestamp BIGINT
        );
        """)
        cur.execute("SELECT COUNT(*) FROM gifts;")
        if cur.fetchone()['count'] == 0:
            sample = [
                ("Модель Breyer Catch Me", "Можно выловить на Авито", "https://www.breyerhorses.com/products/catch-me", "Самые желанные"),
                ("Instax фотоаппарат мгновенной печати", "Или беленький полароид, но он, кажется, ещё дороже :(", "https://www.ozon.ru/product/fotoapparat-mgnovennoy-pechati-fujifilm-mini-12-zelenyy-1047331780", "Самые желанные"),
                ("Сессия с психологом", "", "", "Здоровье"),
                ("МРФ-ролик", "", "", "Здоровье"),
                ("Ручной отпариватель", "", "", "Полезности"),
                ("Суповые тарелочки", "", "https://www.ozon.ru/product/tarelka-glubokaya-supovaya-1-1-l-magistro-tserera-salatnik-farforovyy-tsvet-seryy-496865823/", "Полезности"),
                ("Набор кухонных полотенец из икеи", "Пример по ссылке", "https://www.ozon.ru/product/ikea-rinnig-polotentse-kuhonnoe-belyy-temno-seryy-s-risunkom-45x60-sm-1664361323/", "Полезности"),
                ("Диффузор Hygge #4", "Источник гармонии", "", "Приятности"),
                ("Скраб для тела", "Обожаю лемонграсс или что-то подобное", "", "Приятности"),
                ("Энзимная пудра для умывания", "", "", "Приятности"),
                ("Протеиновые вкусняхи", "(без шоколада, пример по ссылке)", "https://www.ozon.ru/product/fitnesshock-proteinovoe-pechene-bez-sahara-biskvit-romovaya-baba-10-sht-1683729709/", "Приятности"),
                ("Сертификаты Ozon, Золотое Яблоко", "", "", "Универсальное"),
                ("Подписка тг премиум", "", "", "Универсальное")
            ]
            for i, s in enumerate(sample, 1):
                cur.execute("INSERT INTO gifts (id, title, description, link, category) VALUES (%s, %s, %s, %s, %s);", (i, *s))
    return conn

db = get_db()

@app.route('/wishlist')
def wishlist():
    with db.cursor() as cur:
        cur.execute('SELECT id, title, description, link, category FROM gifts;')
        gifts = []
        for row in cur.fetchall():
            cur.execute('SELECT count(*) FROM reserves WHERE gift_id=%s;', (row['id'],))
            reserved = cur.fetchone()['count'] > 0
            gifts.append(dict(id=row['id'], title=row['title'], desc=row['description'], link=row['link'], category=row['category'], reserved=reserved))
        return jsonify(gifts)

@app.route('/reserve', methods=['POST'])
def reserve():
    data = request.json
    user = data.get('user')
    gift_id = data.get('gift_id')
    tg_id, uname = user.get('id'), user.get('username', '')

    if not tg_id:
        return jsonify({"error": "user id missing"}), 400

    with db.cursor() as cur:
        cur.execute('SELECT count(*) FROM reserves WHERE tg_id=%s;', (tg_id,))
        if cur.fetchone()['count'] >= 3:
            return jsonify({"error": "limit reached"}), 400

        cur.execute('SELECT 1 FROM reserves WHERE gift_id=%s;', (gift_id,))
        if cur.fetchone():
            return jsonify({"error": "already reserved"}), 400

        cur.execute('INSERT INTO reserves VALUES (%s, %s, %s, %s);', (gift_id, tg_id, uname, int(time.time())))
        return jsonify({"ok": True})

@app.route('/admin')
def admin():
    user = request.args
    uid = user.get("id")
    if str(uid) not in map(str, ADMIN_IDS) or not verify_telegram(user):
        return "No access", 403

    with db.cursor() as cur:
        cur.execute('SELECT gift_id, tg_id, username, timestamp FROM reserves;')
        rows = cur.fetchall()

    html_out = '<h1>Админка</h1>\n<table><tr><th>Подарок</th><th>ID</th><th>Логин</th><th>Время</th><th>Сброс</th></tr>'
    for r in rows:
        link = f'/admin/reset?gift_id={r["gift_id"]}&id={uid}&hash={user["hash"]}&auth_date={user["auth_date"]}&username={user.get("username", "")}'
        html_out += f'<tr><td>{r["gift_id"]}</td><td>{r["tg_id"]}</td><td>@{html.escape(r["username"] or "")}</td><td>{time.ctime(r["timestamp"])}</td>' \
                    f'<td><a href="{link}">Сброс</a></td></tr>'
    html_out += '</table>'
    return html_out

@app.route('/admin/reset')
def reset():
    user = request.args
    uid = user.get("id")
    if str(uid) not in map(str, ADMIN_IDS) or not verify_telegram(user):
        return "No access", 403

    gift_id = int(user.get('gift_id', 0))
    with db.cursor() as cur:
        cur.execute('DELETE FROM reserves WHERE gift_id=%s;', (gift_id,))
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
