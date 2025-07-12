from flask import Flask, request, jsonify, render_template
import sqlite3, time, hmac, hashlib, os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [877872483]

def verify_telegram(data):
    check = "\n".join(f"{k}={data[k]}" for k in sorted(data) if k != 'hash')
    secret = hashlib.sha256(BOT_TOKEN.encode()).digest()
    if hmac.new(secret, check.encode(), hashlib.sha256).hexdigest() != data['hash']:
        return False
    if time.time() - int(data.get('auth_date', 0)) > 86400:
        return False
    return True

def get_db():
    conn = sqlite3.connect('db.sqlite', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS gifts(id INTEGER PRIMARY KEY, title, description, link)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS reserves(gift_id, tg_id, username, timestamp)''')
    return conn

db = get_db()

@app.route('/wishlist')
def wishlist():
    cur = db.execute('SELECT * FROM gifts')
    gifts = []
    for row in cur.fetchall():
        status = db.execute('SELECT count(*) FROM reserves WHERE gift_id=?',(row[0],)).fetchone()[0]>0
        gifts.append(dict(id=row[0],title=row[1],desc=row[2],link=row[3], reserved=status))
    return jsonify(gifts)

@app.route('/reserve', methods=['POST'])
def reserve():
    data = request.json
    user = data.get('user')
    gift_id = data.get('gift_id')
    if not verify_telegram(user): return jsonify({"error":"auth failed"}),403
    tg_id, uname = user['id'], user.get('username','')
    cnt = db.execute('SELECT count(*) FROM reserves WHERE tg_id=?',(tg_id,)).fetchone()[0]
    if cnt>=3: return jsonify({"error":"limit reached"}),400
    if db.execute('SELECT 1 FROM reserves WHERE gift_id=?',(gift_id,)).fetchone():
        return jsonify({"error":"already reserved"}),400
    db.execute('INSERT INTO reserves VALUES(?,?,?,?)',(gift_id, tg_id, uname, int(time.time())))
    db.commit()
    return jsonify({"ok":True})

@app.route('/admin')
def admin():
    user = request.args
    if str(user.get("id")) not in map(str, ADMIN_IDS) or not verify_telegram(user): return "No access",403
    rows = db.execute('SELECT gift_id, tg_id, username, timestamp FROM reserves').fetchall()
    html = '<h1>Админка</h1>\n<table><tr><th>Подарок</th><th>ID</th><th>Логин</th><th>Время</th><th>Сброс</th></tr>'
    for g,tid,un,ts in rows:
        html+=f'<tr><td>{g}</td><td>{tid}</td><td>@{un}</td><td>{time.ctime(ts)}</td>'\
              f'<td><a href="/admin/reset?gift_id={g}&id={tid}&hash={user["hash"]}&auth_date={user["auth_date"]}&id={user["id"]}&username={user.get("username","")}">Сброс</a></td></tr>'
    html+='</table>'
    return html

@app.route('/admin/reset')
def reset():
    # авторизация и верификация аналогично
    gift_id = request.args['gift_id']
    db.execute('DELETE FROM reserves WHERE gift_id=?',(gift_id,))
    db.commit()
    return "OK"

@app.route('/init')
def init_db():
    sample = [
        (1, "Модель Breyer Catch Me", "Можно выловить на Авито", "https://www.breyerhorses.com/products/catch-me"),
        (2, "Instax фотоаппарат", "Или белый Polaroid, но он дороже", "https://www.ozon.ru/product/fotoapparat-mgnovennoy-pechati-fujifilm-mini-12-zelenyy-1047331780/?at=..."),
        (3, "Сессия с психологом", "", ""),
        (4, "МРФ-ролик", "", ""),
        (5, "Ручной отпариватель", "", "")
    ]
    db.executemany('INSERT OR IGNORE INTO gifts VALUES (?,?,?,?)', sample)
    db.commit()
    return "База заполнена"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
