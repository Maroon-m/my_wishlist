from flask import Flask, request, jsonify
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
            given BOOLEAN DEFAULT FALSE
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
                ("Модель Breyer Catch Me", "Можно выловить на <a href='https://www.avito.ru/sankt-peterburg/kollektsionirovanie/loshad_breyer_traditional_catch_me_19_7299481316' target='_blank'>Авито</a>"
, "https://www.breyerhorses.com/products/catch-me", "Самые желанные"),
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
        return jsonify({"error": "Ошибка входа, обратись к администратору сайта"}), 400

    with db.cursor() as cur:
        cur.execute('SELECT count(*) FROM reserves WHERE tg_id=%s;', (tg_id,))
        if cur.fetchone()['count'] >= 3:
            cur.execute(
            "INSERT INTO overlimit_attempts VALUES (%s, %s, %s);",
            (tg_id, uname, int(time.time()))
            )
            return jsonify({"error": "Ты не можешь забронировать больше трех подарков"}), 400

        cur.execute('SELECT 1 FROM reserves WHERE gift_id=%s;', (gift_id,))
        if cur.fetchone():
            return jsonify({"error": "Этот подарок уже забронирован"}), 400

        cur.execute('INSERT INTO reserves VALUES (%s, %s, %s, %s);', (gift_id, tg_id, uname, int(time.time())))
        return jsonify({"ok": True})

@app.route('/admin')
def admin():
    user = request.args
    uid = user.get("id")
    if str(uid) not in map(str, ADMIN_IDS) or not verify_telegram(user):
        return "No access", 403

    tz_msk = timezone(timedelta(hours=3))  # МСК

    with db.cursor() as cur:
        cur.execute('SELECT gift_id, tg_id, username, timestamp FROM reserves;')
        rows = cur.fetchall()

    html_out = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
      <meta charset="UTF-8">
      <title>Админка</title>
      <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 32px; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
        .clickable {{ cursor: pointer; color: #999; }}
      </style>
      <script>
        function reveal(span, text) {{
          span.innerText = text;
          span.style.color = '#000';
        }}
      </script>
    </head>
    <body>
    <h1>Админка</h1>
    <p><a href="/admin/gifts?id={uid}&username={user.get("username")}&auth_date={user.get("auth_date")}&hash={user.get("hash")}">Управление подарками</a></p>
    <table>
      <tr><th>Подарок</th><th>ID</th><th>Логин</th><th>Время (МСК)</th><th>Сброс</th></tr>
    """


    for r in rows:
        dt = datetime.fromtimestamp(r["timestamp"], tz=tz_msk).strftime("%Y-%m-%d %H:%M:%S")
        link = f'/admin/reset?gift_id={r["gift_id"]}&id={uid}&hash={user["hash"]}&auth_date={user["auth_date"]}&username={user.get("username", "")}'
        uname = html.escape(r["username"] or "")
        html_out += f"""
        <tr>
          <td><span class="clickable" onclick="reveal(this, '{r["gift_id"]}')">👁 Рассекретить</span></td>
          <td>{r["tg_id"]}</td>
          <td><span class="clickable" onclick="reveal(this, '@{uname}')">👁 Рассекретить</span></td>
          <td>{dt}</td>
          <td><a href="{link}">Сброс</a></td>
        </tr>"""

    html_out += "</table>"

    with db.cursor() as cur:
        cur.execute("SELECT tg_id, username, timestamp FROM overlimit_attempts ORDER BY timestamp DESC LIMIT 10;")
        attempts = cur.fetchall()

    html_out += "<h2>Попытки переброни</h2>\n<table><tr><th>ID</th><th>Логин</th><th>Время (МСК)</th></tr>"
    for a in attempts:
        dt = datetime.fromtimestamp(a["timestamp"], tz=tz_msk).strftime("%Y-%m-%d %H:%M:%S")
        uname = html.escape(a["username"] or "")
        html_out += f"""
        <tr>
          <td>{a["tg_id"]}</td>
          <td><span class="clickable" onclick="reveal(this, '@{uname}')">👁 Рассекретить</span></td>
          <td>{dt}</td>
        </tr>
        """

    html_out += "</table></body></html>"
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

@app.route('/admin/gifts', methods=['GET', 'POST'])
def edit_gifts():
    user = request.args
    uid = user.get("id")
    if str(uid) not in map(str, ADMIN_IDS) or not verify_telegram(user):
        return "No access", 403

    with db.cursor() as cur:
        # Обработка POST (изменения)
        if request.method == 'POST':
            action = request.form.get('action')
            gift_id = request.form.get('gift_id')
            if action == 'delete':
                cur.execute('DELETE FROM gifts WHERE id=%s;', (gift_id,))
            elif action == 'toggle_given':
                cur.execute('UPDATE gifts SET given = NOT given WHERE id=%s;', (gift_id,))
            return redirect(request.url)

        # GET
        cur.execute("SELECT * FROM gifts ORDER BY category, id;")
        gifts = cur.fetchall()

    # Простая HTML-форма
    html_out = """
    <h1>Управление подарками</h1>
    <table border="1" cellpadding="8">
    <tr><th>ID</th><th>Название</th><th>Категория</th><th>Действия</th></tr>
    """
    for g in gifts:
        html_out += f"""
        <tr>
            <td>{g['id']}</td>
            <td>{html.escape(g['title'])}</td>
            <td>{html.escape(g['category'])}</td>
            <td>
                <form method="post" style="display:inline">
                    <input type="hidden" name="gift_id" value="{g['id']}">
                    <button name="action" value="delete">Удалить</button>
                </form>
                <form method="post" style="display:inline">
                    <input type="hidden" name="gift_id" value="{g['id']}">
                    <button name="action" value="toggle_given">
                        {'Убрать статус' if g['given'] else 'Отметить подаренным'}
                    </button>
                </form>
            </td>
        </tr>
        """
    html_out += "</table>"
    return html_out

@app.route('/admin/gifts')
def admin_gifts():
    user = request.args
    uid = user.get("id")
    if str(uid) not in map(str, ADMIN_IDS) or not verify_telegram(user):
        return "No access", 403

    with db.cursor() as cur:
        cur.execute('SELECT * FROM gifts ORDER BY category, id;')
        gifts = cur.fetchall()

    html = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
      <meta charset="UTF-8">
      <title>Редактировать подарки</title>
      <style>
        body { font-family: sans-serif; padding: 20px; max-width: 800px; margin: auto; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 32px; }
        th, td { border: 1px solid #ccc; padding: 6px 10px; }
        th { background: #eee; }
        input, textarea { width: 100%; margin-bottom: 6px; }
        .given { color: gray; text-decoration: line-through; }
      </style>
    </head>
    <body>
      <h1>Редактор подарков</h1>

      <h2>Добавить новый</h2>
      <form method="post" action="/admin/gift/add?id={{id}}&username={{username}}&auth_date={{auth_date}}&hash={{hash}}">
        <p><input name="title" placeholder="Название" required></p>
        <p><textarea name="description" placeholder="Описание"></textarea></p>
        <p><input name="link" placeholder="Ссылка (необязательно)"></p>
        <p><input name="category" placeholder="Категория" required></p>
        <p><button type="submit">Добавить</button></p>
      </form>

      <h2>Существующие подарки</h2>
      <table>
        <tr><th>ID</th><th>Название</th><th>Категория</th><th>Статус</th><th>Действия</th></tr>
        {% for g in gifts %}
          <tr class="{{ 'given' if g['given'] else '' }}">
            <td>{{ g['id'] }}</td>
            <td>{{ g['title'] }}</td>
            <td>{{ g['category'] }}</td>
            <td>{{ 'Подарено' if g['given'] else 'Ожидает' }}</td>
            <td>
              <form method="post" action="/admin/gift/delete?id={{id}}&username={{username}}&auth_date={{auth_date}}&hash={{hash}}" style="display:inline;">
                <input type="hidden" name="id" value="{{ g['id'] }}">
                <button type="submit">Удалить</button>
              </form>
              {% if not g['given'] %}
              <form method="post" action="/admin/gift/given?id={{id}}&username={{username}}&auth_date={{auth_date}}&hash={{hash}}" style="display:inline;">
                <input type="hidden" name="id" value="{{ g['id'] }}">
                <button type="submit">Подарено</button>
              </form>
              {% endif %}
            </td>
          </tr>
        {% endfor %}
      </table>
    </body>
    </html>
    """

    return render_template_string(html,
        gifts=gifts,
        id=uid,
        username=user.get("username"),
        auth_date=user.get("auth_date"),
        hash=user.get("hash")
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
