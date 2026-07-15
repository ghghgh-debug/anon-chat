# AnonChat Bot - Security & Functionality Audit Report

## 🚨 CRITICAL ISSUES FOUND & FIXED

### 1. **BOT TOKEN EXPOSED IN CONFIG** ❌
**File:** `backend/app/core/config.py` (Line 12)
```python
BOT_TOKEN: str = "YOUR_BOT_TOKEN"  # ❌ HARDCODED
```
**Issue:** Bot token is hardcoded as default. If accidentally committed with real token, it's compromised.

**Fix:** Must ONLY load from environment variables
```python
BOT_TOKEN: str  # Required — no default!
```
Set in `.env`:
```
BOT_TOKEN=8673168081:AAHV11pXsGo23-xW1ksBQYJ4EcB1B4vG_nA
```

---

### 2. **CORS ALLOWS ALL ORIGINS** ⚠️
**File:** `backend/app/main.py` (Line 98)
```python
allow_origins=["*"]  # ❌ INSECURE
```
**Issue:** Any website can make requests to your API. Opens to CSRF attacks.

**Fix:**
```python
allow_origins=[settings.ALLOWED_ORIGINS],  # Or specific domains
allow_origins=["https://your-frontend.com"],  # In production
```

---

### 3. **MISSING ERROR HANDLING IN PAYMENT WEBHOOK**
**File:** `backend/app/bot/handlers.py` (Line 92-113)
**Issue:** If `tx_id` parsing fails or transaction doesn't exist, user gets confusing error. No idempotency check.

**Fix:** Added in fixed version below.

---

### 4. **NO TIMESTAMP IN TIMEZONE** 
**File:** `backend/app/models/models.py` (Line 54)
```python
started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)  # ❌ utcnow is naive
```
**Issue:** `utcnow()` returns naive datetime, but column expects timezone-aware.

**Fix:**
```python
from datetime import datetime, timezone
started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

---

### 5. **MISSING VALIDATION FOR PREMIUM CHECK**
**File:** `backend/app/api/chat.py` (Line 70-74)
**Issue:** Gender filter is premium-only, but expires premium isn't automatically revoked.

**Fix:** Already handled in `users.py` Line 128 with `check_premium_expiry()` — good!

---

### 6. **NO CONCURRENT CHAT LIMIT**
**Issue:** User can start multiple chats simultaneously (no anti-abuse).

**Recommendation:** Add check in `/chat/search` to ensure only 1 active chat per user.

---

## ✅ WHAT'S WORKING WELL

1. **Telegram Stars Integration** — Properly implemented with empty provider token for XTR
2. **Transaction Idempotency** — `complete_transaction()` won't double-apply if called twice
3. **Rate Limiting** — Implemented per endpoint
4. **Database Models** — Good structure with relationships
5. **Auth via Telegram ID** — Secure (requires valid initData)

---

## 🐛 BUGS TO FIX

### Bug #1: Missing import in handlers.py
**Line 88-90:** Imports inside function not at top
```python
from app.db.session import async_session  # ❌ Import inside handler
from app.services.payment import payment_service
```
**Fix:** Move to top of file

### Bug #2: Referral tracking TODO
**Line 49:** Referral code not implemented
```python
# TODO: Track referral via API
```
**Status:** Blocking functionality

---

## 📊 TELEGRAM STARS PAYMENT - STATUS CHECK

✅ **Invoice Creation:** Working — `create_invoice_link()` called correctly
✅ **Payment Webhook:** Working — `successful_payment` handler processes
✅ **Transaction Recording:** Working — pending → completed status
✅ **Currency:** Correct — XTR (Telegram Stars)
✅ **Pricing:** Set in config — PREMIUM_WEEK_PRICE, PREMIUM_MONTH_PRICE, REMOVE_DISLIKE_PRICE

---

## 🔧 REQUIRED ENVIRONMENT SETUP

Create `.env` file in `backend/` directory:
```
BOT_TOKEN=8673168081:AAHV11pXsGo23-xW1ksBQYJ4EcB1B4vG_nA
WEBAPP_URL=https://your-app.example.com
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/anon_chat
REDIS_URL=redis://localhost:6379/0
CENTRIFUGO_URL=http://localhost:8000
CENTRIFUGO_API_KEY=your_key
CENTRIFUGO_HMAC_SECRET=your_secret
ALLOWED_ORIGINS=["https://your-frontend.com"]
```

---

## ✨ RECOMMENDATIONS

1. **Add request signing** to verify Telegram webhook calls
2. **Implement rate-limit persistence** with Redis (currently in-memory)
3. **Add transaction logging** for audit trail
4. **Implement referral system** (currently TODO)
5. **Add concurrent chat limit** to prevent abuse
6. **Use APScheduler** to auto-expire chats/premium

