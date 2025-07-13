from flask import Flask, request, jsonify, redirect
import time, hmac, hashlib, os, html
from datetime import datetime, timedelta, timezone
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
            category TEXT,
            is_given BOOLEAN DEFAULT FALSE
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
        cur.execute("""
        CREATE TABLE IF NOT EXISTS overlimit_attempts (
            tg_id BIGINT,
            username TEXT,
            timestamp BIGINT
        );
        """)

        cur.execute("SELECT COUNT(*) FROM gifts;")
        if cur.fetchone()['count'] == 0:
            sample = [
                ("Модель Breyer Catch Me", "Можно выловить на <a href='https://www.avito.ru/sankt-peterburg/kollektsionirovanie/loshad_breyer_traditional_catch_me_19_7299481316' target='_blank'>Авито</a>", "https://www.breyerhorses.com/products/catch-me", "Самые желанные"),
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
                ("Креативные серьги", "", "", "Приятности"),
                ("Сертификаты Ozon, Золотое Яблоко", "", "", "Универсальное"),
                ("Подписка тг премиум", "", "", "Универсальное"),
                ("Игровая приставка Sony PlayStation 5", "", "", "Данила, ты что, крейзи?"),
                ("Виниловый проигрыватель", "", "", "Данила, ты что, крейзи?"),
                ("Компактная рожковая кофемашина", "", "", "Данила, ты что, крейзи?"),
            ]
            for i, s in enumerate(sample, 1):
                cur.execute("INSERT INTO gifts (id, title, description, link, category) VALUES (%s, %s, %s, %s, %s);", (i, *s))
    return conn

db = get_db()

@app.route('/wishlist')
def wishlist():
    uid = request.args.get("id")
    is_admin = str(uid) in map(str, ADMIN_IDS)
    with db.cursor() as cur:
        cur.execute('SELECT id, title, description, link, category, is_given FROM gifts ORDER BY category, id;')
        rows = cur.fetchall()

        gifts = []
        for row in rows:
            cur.execute('SELECT count(*) FROM reserves WHERE gift_id=%s;', (row['id'],))
            reserved = cur.fetchone()['count'] > 0
            if reserved and not is_admin:
                continue
            gifts.append(dict(
                id=row['id'],
                title=row['title'],
                desc=row['description'],
                link=row['link'],
                category=row['category'],
                reserved=reserved,
                given=row['is_given']
            ))
        return jsonify(gifts)

@app.route('/reserve', methods=['POST'])
def reserve():
    data = request.json
    user = data.get('user')
    gift_id = data.get('gift_id')
    tg_id, uname = user.get('id'), user.get('username', '')

    if not tg_id:
        return jsonify({"error": "Ошибка входа, обратись к администратору сайта"}), 400

    with db.cursor() as cur:
        cur.execute('SELECT count(*) FROM reserves WHERE tg_id=%s;', (tg_id,))
        if cur.fetchone()['count'] >= 3:
            cur.execute("INSERT INTO overlimit_attempts VALUES (%s, %s, %s);", (tg_id, uname, int(time.time())))
            return jsonify({"error": "Ты не можешь забронировать больше трех подарков"}), 400

        cur.execute('SELECT 1 FROM reserves WHERE gift_id=%s;', (gift_id,))
        if cur.fetchone():
            return jsonify({"error": "Этот подарок уже забронирован"}), 400

        cur.execute('INSERT INTO reserves VALUES (%s, %s, %s, %s);', (gift_id, tg_id, uname, int(time.time())))
        return jsonify({"ok": True})

@app.route('/admin/gift/add', methods=['POST'])
def add_gift():
    user = request.args
    if str(user.get("id")) not in map(str, ADMIN_IDS) or not verify_telegram(user):
        return "No access", 403

    data = request.json
    with db.cursor() as cur:
        cur.execute("INSERT INTO gifts (title, description, link, category) VALUES (%s, %s, %s, %s);",
                    (data['title'], data['description'], data['link'], data['category']))
    return "OK"

@app.route('/admin/gift/delete', methods=['POST'])
def delete_gift():
    user = request.args
    if str(user.get("id")) not in map(str, ADMIN_IDS) or not verify_telegram(user):
        return "No access", 403

    data = request.json
    with db.cursor() as cur:
        cur.execute("DELETE FROM gifts WHERE id=%s;", (data['id'],))
        cur.execute("DELETE FROM reserves WHERE gift_id=%s;", (data['id'],))
    return "OK"

@app.route('/admin/gift/update', methods=['POST'])
def update_gift():
    user = request.args
    if str(user.get("id")) not in map(str, ADMIN_IDS) or not verify_telegram(user):
        return "No access", 403

    data = request.json
    with db.cursor() as cur:
        cur.execute("UPDATE gifts SET title=%s, description=%s, link=%s, category=%s WHERE id=%s;",
                    (data['title'], data['description'], data['link'], data['category'], data['id']))
    return "OK"

@app.route('/admin/gift/given', methods=['POST'])
def mark_given():
    user = request.args
    if str(user.get("id")) not in map(str, ADMIN_IDS) or not verify_telegram(user):
        return "No access", 403

    data = request.json
    with db.cursor() as cur:
        cur.execute("UPDATE gifts SET is_given=%s WHERE id=%s;", (data['given'], data['id']))
    return "OK"

@app.route('/admin/reset')
def reset():
    user = request.args
    if str(user.get("id")) not in map(str, ADMIN_IDS) or not verify_telegram(user):
        return "No access", 403

    gift_id = int(user.get('gift_id', 0))
    with db.cursor() as cur:
        cur.execute('DELETE FROM reserves WHERE gift_id=%s;', (gift_id,))
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
