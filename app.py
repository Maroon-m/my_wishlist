from flask import Flask, request, jsonify, render_template
import sqlite3, time, hmac, hashlib, os
from flask_cors import CORS
import html

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [877872483]

def verify_telegram(data):
    check = "\n".join(f"{k}={data[k]}" for k in sorted(data) if (k != 'hash' and k != 'gift_id'))
    secret = hashlib.sha256(BOT_TOKEN.encode()).digest()
    if hmac.new(secret, check.encode(), hashlib.sha256).hexdigest() != data['hash']:
        return False
    if time.time() - int(data.get('auth_date', 0)) > 86400:
        return False
    return True



def get_db():
    conn = sqlite3.connect('db.sqlite', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS gifts(id INTEGER PRIMARY KEY, title, description, link, category)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS reserves(gift_id, tg_id, username, timestamp)''')

    cur = conn.execute('SELECT COUNT(*) FROM gifts')
    if cur.fetchone()[0] == 0:
        sample = [
            (1, "Модель Breyer Catch Me", "Можно выловить на Авито", "https://www.breyerhorses.com/products/catch-me", "Самые желанные"),
            (2, "Instax фотоаппарат мгновенной печати", "Или беленький полароид, но он, кажется, ещё дороже :(", "https://www.ozon.ru/product/fotoapparat-mgnovennoy-pechati-fujifilm-mini-12-zelenyy-1047331780/?at=DqtD7yOAAS5PvzxzHJl6BlPuJNJGRvHGMDmR3F3MgK4M", "Самые желанные"),
            (3, "Сессия с психологом", "", "", "Полезности"),
            (4, "МРФ-ролик", "", "", "Полезности"),
            (5, "Ручной отпариватель", "", "", "Полезности"),
            (6, "Набор кухонных полотенец из икеи", "", "", "Полезности"),
            (7, "Диффузор Hygge #4", "Источник гармонии", "", "Приятности"),
            (8, "Скраб для тела", "Обожаю лемонграсс или что-то подобное", "", "Приятности"),
            (9, "Энзимная пудра для умывания", "", "", "Приятности"),
            (10, "Протеиновые вкусняхи", "(без шоколада)", "", "Приятности"),
            (11, "Сертификаты Ozon, Золотое Яблоко", "", "", "Универсальное")
        ]
        conn.executemany('INSERT INTO gifts VALUES (?,?,?,?,?)', sample)
        conn.commit()

    return conn


db = get_db()

@app.route('/wishlist')
def wishlist():
    cur = db.execute('SELECT id, title, description, link, category FROM gifts')
    gifts = []
    for row in cur.fetchall():
        reserved = db.execute('SELECT count(*) FROM reserves WHERE gift_id=?', (row[0],)).fetchone()[0] > 0
        gifts.append(dict(id=row[0], title=row[1], desc=row[2], link=row[3], category=row[4], reserved=reserved))
    return jsonify(gifts)

@app.route('/reserve', methods=['POST'])
def reserve():
    data = request.json
    user = data.get('user')
    gift_id = data.get('gift_id')
    if not verify_telegram(user): return jsonify({"error": "auth failed"}), 403
    tg_id, uname = user['id'], user.get('username', '')
    cnt = db.execute('SELECT count(*) FROM reserves WHERE tg_id=?', (tg_id,)).fetchone()[0]
    if cnt >= 3: return jsonify({"error": "limit reached"}), 400
    if db.execute('SELECT 1 FROM reserves WHERE gift_id=?', (gift_id,)).fetchone():
        return jsonify({"error": "already reserved"}), 400
    db.execute('INSERT INTO reserves VALUES (?, ?, ?, ?)', (gift_id, tg_id, uname, int(time.time())))
    db.commit()
    return jsonify({"ok": True})

@app.route('/admin')
def admin():
    user = request.args
    uid = user.get("id")
    if str(uid) not in map(str, ADMIN_IDS) or not verify_telegram(user):
        return "No access", 403

    rows = db.execute('SELECT gift_id, tg_id, username, timestamp FROM reserves').fetchall()
    html_out = '<h1>Админка</h1>\n<table><tr><th>Подарок</th><th>ID</th><th>Логин</th><th>Время</th><th>Сброс</th></tr>'
    for g, tid, un, ts in rows:
        link = f'/admin/reset?gift_id={g}&id={uid}&hash={user["hash"]}&auth_date={user["auth_date"]}&username={user.get("username", "")}'
        html_out += f'<tr><td>{g}</td><td>{tid}</td><td>@{html.escape(un)}</td><td>{time.ctime(ts)}</td>' \
                    f'<td><a href="{link}">Сброс</a></td></tr>'
    html_out += '</table>'
    return html_out

@app.route('/admin/reset')
def reset():
    user = request.args
    uid = user.get("id")
    if str(uid) not in map(str, ADMIN_IDS) or not verify_telegram(user):
        return "No access", 403

    gift_id = user.get('gift_id')
    db.execute('DELETE FROM reserves WHERE gift_id=?', (gift_id,))
    db.commit()
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
