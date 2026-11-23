# Руководство по развертыванию Psycho Stars на Ubuntu VPS

Это пошаговая инструкция для production-деплоя Telegram Mini App магазина **Psycho Stars** на стандартном виртуальном сервере с Ubuntu 22.04 / 24.04 LTS.

---

## 1. Требования к серверу
- **ОС**: Ubuntu 22.04 LTS или 24.04 LTS
- **Конфигурация**: Минимум 1 vCPU, 2 ГБ RAM, 20 ГБ NVMe/SSD
- **Домен**: Привязанный к IP вашего сервера домен (например, `stars.yourdomain.com`). Mini App **обязан** работать по HTTPS с валидным сертификатом (Caddy выпустит Let's Encrypt автоматически).

---

## 2. Подготовка сервера и установка Docker

Подключитесь к серверу по SSH и выполните:

```bash
# 1. Обновление пакетов
sudo apt update && sudo apt upgrade -y

# 2. Установка базовых утилит
sudo apt install -y curl git ufw fail2ban jq

# 3. Настройка фаервола (UFW)
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# 4. Установка Docker и Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Примените изменения группы
newgrp docker
docker --version
docker compose version
```

---

## 3. Клонирование и настройка проекта

```bash
# Клонируйте проект в рабочую папку
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ> /opt/psycho-stars
cd /opt/psycho-stars

# Скопируйте шаблон переменных окружения
cp .env.example .env
```

Отредактируйте файл `.env`:
```bash
nano .env
```

### Важные параметры `.env`:
1. **APP_DOMAIN**: Ваш домен (например, `stars.yourdomain.com`). Caddy автоматически получит SSL для этого домена.
2. **ACME_EMAIL**: Ваша почта для Let's Encrypt сертификата.
3. **BOT_TOKEN**: Токен вашего бота из [@BotFather](https://t.me/BotFather).
4. **MINI_APP_URL**: Ссылка на фронтенд, e.g. `https://stars.yourdomain.com`.
5. **ADMIN_IDS**: Ваш Telegram ID (узнать можно в @userinfobot), например `123456789,987654321`.
6. **SECRET_KEY**: Сгенерируйте случайную строку: `openssl rand -hex 32`.
7. **CRYPTOBOT_API_TOKEN**: Токен мерчанта из [@CryptoBot](https://t.me/CryptoBot) (`/pay` -> `Create App`).
8. **LAVAPAY_SHOP_ID & LAVAPAY_SECRET_KEY**: Данные мерчанта из личного кабинета Lava (lava.so / lava.ru).
9. **TON_WALLET_MNEMONIC**: 24 слова мнемоники кошелька TON магазина. Храните только в `.env`!
10. **DRY_RUN_FULFILLMENT**: Для тестирования без списания реальных TON держите `true`. В реальном проде переключите на `false`.

---

## 4. Настройка Telegram Mini App в @BotFather

1. Откройте [@BotFather](https://t.me/BotFather) и выберите своего бота: `/mybots` -> выберите бота.
2. Перейдите в **Bot Settings** -> **Menu Button** -> **Configure menu button**.
3. Укажите URL: `https://stars.yourdomain.com` и название кнопки: `⭐ Магазин`.
4. Включите команду `/newapp` в BotFather, чтобы зарегистрировать Mini App с прямой ссылкой (например, `t.me/PsychoStarsBot/store`).

---

## 5. Настройка вебхуков в платежных шлюзах

В панелях провайдеров укажите URL вебхуков:
- **CryptoBot Webhook URL**:
  `https://stars.yourdomain.com/api/v1/webhooks/cryptobot`
- **Lava Pay Webhook URL**:
  `https://stars.yourdomain.com/api/v1/webhooks/lavapay`

Подписи вебхуков валидируются сервером автоматически по сырому телу запроса (HMAC-SHA256).

---

## 6. Запуск системы

```bash
# Сборка и запуск контейнеров в фоне
docker compose up -d --build

# Проверка статуса сервисов
docker compose ps
```

Вы должны увидеть:
- `psycho_stars_caddy` (healthy/running)
- `psycho_stars_backend` (healthy)
- `psycho_stars_worker` (running)
- `psycho_stars_bot` (running)
- `psycho_stars_postgres` (healthy)
- `psycho_stars_redis` (healthy)

---

## 7. Заполнение каталога начальными товарами (Seed)

Выполните команду внутри контейнера бэкенда для создания категорий (Stars, Premium) и продуктов:

```bash
docker compose exec backend python scripts/seed_catalog.py
```

---

## 8. Автоматические бэкапы базы данных (Cron)

Добавьте скрипт резервного копирования в системный crontab:

```bash
crontab -e
```

Вставьте строку для запуска бэкапа каждый день в 03:00 ночи:
```cron
0 3 * * * /opt/psycho-stars/scripts/backup_db.sh >> /var/log/psycho_backup.log 2>&1
```

---

## 9. Полезные команды для обслуживания

```bash
# Просмотр логов бэкенда
docker compose logs -f backend

# Просмотр логов фонового воркера (выдача и TON)
docker compose logs -f worker

# Просмотр логов бота
docker compose logs -f bot

# Перезапуск сервисов
docker compose restart

# Остановка проекта
docker compose down
```
