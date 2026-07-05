# Развёртывание приложения «Кадастр объектов недвижимости»

Приложение разворачивается на [Render.com](https://render.com) — бесплатно, автоматически, за 5 минут.

## Что нужно

- Аккаунт на [GitHub](https://github.com) (чтобы форкнуть репозиторий)
- Аккаунт на [Render.com](https://render.com) (можно войти через GitHub)

## Шаг 1. Форкните репозиторий

1. Откройте https://github.com/Marina-Arties/cadastre
2. Нажмите кнопку **Fork** (в правом верхнем углу)
3. Нажмите **Create fork**

## Шаг 2. Подключите к Render.com

1. Откройте https://dashboard.render.com
2. Нажмите **New +** → **Blueprint**
3. Нажмите **Connect GitHub** и выберите ваш форк репозитория
4. Нажмите **Apply**

Render сам создаст:
- Веб-сервер (FastAPI + Uvicorn)
- Базу данных PostgreSQL

Деплой займёт 3-5 минут. Вы увидите зелёный статус **Live**.

## Шаг 3. Войдите в приложение

Перейдите по ссылке вида `https://cadastre-xxxx.onrender.com`

Учётные данные администратора (создаются автоматически):
- **Email**: `admin@cadastre.ru`
- **Пароль**: `Admin123`

**Сразу после входа смените пароль администратора** в Личном кабинете.

## Альтернативный способ: PythonAnywhere

Если Render.com по каким-то причинам не подходит, приложение можно развернуть на [PythonAnywhere.com](https://pythonanywhere.com):

1. Зарегистрируйтесь, создайте веб-приложение (Flask/Python 3.10+)
2. Загрузите содержимое папки `backend` через вкладку **Files**
3. В настройках веб-приложения укажите:
   - **Source code**: `/home/вашлогин/backend`
   - **Working directory**: `/home/вашлогин/backend`
   - **WSGI configuration file** — замените содержимое на:
     ```python
     import sys
     sys.path.insert(0, '/home/вашлогин/backend')
     from app.main import app
     application = app
     ```
4. Нажмите **Reload**

---

## Лицензия

MIT. Код открыт для использования и доработки.
