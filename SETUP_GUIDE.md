# Setup Guide: AnonChat Telegram Mini App

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 12+
- Redis 6+
- Centrifugo (optional, for real-time messaging)

---

## ⚙️ Installation Steps

### 1. Clone Repository
```bash
git clone https://github.com/ghghgh-debug/anon-chat.git
cd anon-chat/backend
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
nano .env  # Edit with your actual values
```

**Critical fields to set:**
- `BOT_TOKEN` — Get from @BotFather
- `WEBAPP_URL` — Your frontend URL
- `DATABASE_URL` — PostgreSQL connection
- `REDIS_URL` — Redis connection
- `ALLOWED_ORIGINS` — Your frontend domain

### 5. Setup Database
```bash
# Using Alembic (if migrations exist)
alembic upgrade head

# Or manually (FastAPI will create tables on startup)
python -m app.main
```

### 6. Run Backend
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🤖 Telegram Bot Setup

### Enable Telegram Stars Payments

1. **Message @BotFather** on Telegram
2. Select your bot
3. Run `/payments`
4. Enable **Telegram Stars** payment method
5. Done! Users can now purchase with stars

### Set Webhook (for production)
```bash
# Replace with your actual domain and bot token
curl -X POST "https://api.telegram.org/bot YOUR_BOT_TOKEN/setWebhook" \
  -F "url=https://your-backend.com/webhook/telegram"
```

---

## 💳 Telegram Stars Payment Flow

### How it works:
1. User clicks "Buy Premium" in app
2. Frontend calls `/api/payments/create-invoice` 
3. Backend creates pending transaction in DB
4. Returns Telegram invoice URL to frontend
5. Frontend opens invoice with `Telegram.WebApp.openInvoice(url)`
6. User completes payment in Telegram
7. Telegram sends webhook to `/webhook/telegram`
8. Handler calls `complete_transaction()` → Premium activated ✅

### Testing Payments (Sandbox Mode)
```python
# In development, use test bot:
BOT_TOKEN=1234567:4TtjnEabc... (test bot token)
# Then payments work without real Telegram Stars
```

---

## 🔒 Security Checklist

- [ ] `BOT_TOKEN` is set in `.env` (not hardcoded)
- [ ] `ALLOWED_ORIGINS` restricts to your frontend domain
- [ ] `DEBUG=False` in production
- [ ] `.env` file is in `.gitignore`
- [ ] PostgreSQL requires authentication
- [ ] Redis requires password
- [ ] HTTPS enabled on production domain
- [ ] Webhook URL is HTTPS only

---

## 📊 Monitoring & Logs

### View logs
```bash
tail -f app.log  # If logging to file
```

### Health check
```bash
curl http://localhost:8000/api/health
```

### Check payments
```bash
curl http://localhost:8000/api/payments/prices \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🐛 Troubleshooting

### Bot doesn't respond
- Check `BOT_TOKEN` is correct
- Run: `curl https://api.telegram.org/botYOUR_TOKEN/getMe`
- Should return bot info

### Payment webhook fails
- Check `/webhook/telegram` is reachable
- Verify webhook URL in BotFather: `/setWebhook`
- Check logs for payload errors

### Database connection refused
- Ensure PostgreSQL is running
- Check `DATABASE_URL` is correct
- Test: `psql postgresql://user:pass@localhost/anon_chat`

### Redis connection fails
- Ensure Redis is running on port 6379
- Test: `redis-cli ping` should return "PONG"

---

## 📝 Environment Variables Explained

| Variable | Description | Example |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token from @BotFather | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `WEBAPP_URL` | Frontend URL for mini app | `https://app.example.com` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@localhost/db` |
| `CENTRIFUGO_HMAC_SECRET` | Secret for signing Centrifugo tokens | `your-super-secret-key-12345` |
| `ALLOWED_ORIGINS` | CORS allowed domains | `["https://app.example.com"]` |
| `PREMIUM_WEEK_PRICE` | Price in Telegram Stars | `99` |

---

## 🚀 Deployment (Production)

### Using Docker
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using Docker Compose
```bash
docker-compose up -d
```

### Set production URL in Telegram
```bash
# After deployment
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook" \
  -F "url=https://your-production-domain.com/webhook/telegram"
```

---

## ✅ Fixed Issues in This Version

1. ✅ **BOT_TOKEN** — No longer hardcoded, loaded from `.env`
2. ✅ **CORS** — Restricted to allowed origins (was `["*"]`)
3. ✅ **Payment Error Handling** — Better logging and error messages
4. ✅ **Timezone Bug** — Using `datetime.now(timezone.utc)` (was naive)
5. ✅ **Imports** — Moved to top of handlers.py (was inside function)

---

## 📞 Support

For issues:
1. Check logs: `grep -i error app.log`
2. Review AUDIT_REPORT.md
3. Check Telegram Bot API docs: https://core.telegram.org/bots/payments
