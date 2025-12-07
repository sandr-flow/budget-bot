# Настройка Telegram бота (Python + Aiogram)

## Шаг 1: Google Cloud Console (сервисный аккаунт)

Для доступа к Google Sheets нужен сервисный аккаунт:

1. Открой [Google Cloud Console](https://console.cloud.google.com/)
2. Создай новый проект (или выбери существующий)
3. В меню слева: **APIs & Services → Library**
4. Найди и включи:
   - **Google Sheets API**
   - **Google Drive API**
5. В меню: **APIs & Services → Credentials**
6. Нажми **Create Credentials → Service Account**
7. Введи имя (любое), нажми **Create**
8. Роли можно пропустить, нажми **Done**
9. Нажми на созданный сервисный аккаунт
10. Вкладка **Keys → Add Key → Create new key → JSON**
11. Скачай JSON файл и переименуй в `credentials.json`
12. Положи `credentials.json` в папку проекта

## Шаг 2: Доступ к таблице

1. Открой скачанный `credentials.json`
2. Найди поле `client_email` (что-то типа `...@...iam.gserviceaccount.com`)
3. Открой свою Google Таблицу
4. Нажми **Share** (Поделиться)
5. Добавь этот email с правами **Editor**

## Шаг 3: Настройка .env

Открой файл `.env` и впиши токен бота от BotFather:

```
BOT_TOKEN=123456:ABC-DEF...
```

## Шаг 4: Установка и запуск

```powershell
# Создай виртуальное окружение (если нет)
python -m venv venv

# Активируй
.\venv\Scripts\Activate

# Установи зависимости
pip install -r requirements.txt

# Запусти бота
python bot.py
```

## Тестирование

1. Напиши боту `/start`
2. Отправь `500 кофе`
3. Выбери категорию
4. Проверь таблицу — данные должны появиться!

## Хостинг (чтобы работал 24/7)

- **Railway.app** — бесплатный tier
- **Render.com** — бесплатный tier
- Или просто запускай на своём ПК когда нужно
