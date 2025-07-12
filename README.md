# Wishlist Backend

Простой сервер на Flask для сайта вишлиста с Telegram-авторизацией и системой бронирования подарков.

## Возможности
- Авторизация через Telegram Login Widget
- Ограничение: до 3 бронирований на одного пользователя
- Отображение забронированных подарков
- Панель администратора со сбросом брони и просмотром username'ов

## Развёртывание на Render

### 1. Установи переменные окружения:
- `BOT_TOKEN` — токен от Telegram-бота

### 2. Команды для Render:
- Build Command: `pip install -r requirements.txt`
- Start Command: `python app.py`
- Environment: Python 3.10+

## Эндпоинты
- `GET /wishlist` — получить список подарков (с флагом бронирования)
- `POST /reserve` — забронировать подарок (принимает `{user, gift_id}`)
- `GET /admin` — просмотр всех броней
- `GET /admin/reset` — сброс брони по gift_id

## Автор
Мария
