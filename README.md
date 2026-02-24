# Railway Ticket Booking System

A simplified Railway Ticket Booking System with both Web UI and REST API, built using:

- Python
- Django
- Django REST Framework
- Redis (Seat Locking)
- Celery (Background Tasks)
- Server-side rendered UI

The system focuses on backend design, data modeling, concurrency handling,
and realistic booking lifecycle simulation.

---

1. Setup & Run Instructions

---

### 1. Clone repository

```bash
git clone https://github.com/Ayushraj1605/Rupeeflo-Assignment.git
cd railway-booking-system
```

### 2. Create and activate virtual environment (Windows)

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root (same level as `manage.py`) with at least:

```env
RAZORPAY_KEY_ID="<your-test-key-id>"
RAZORPAY_KEY_SECRET="<your-test-key-secret>"
RAZORPAY_WEBHOOK_SECRET="<some-webhook-secret>"
```

These are used for Razorpay test payments and webhook verification. For basic local testing without webhooks you can leave the defaults from `config/settings.py`.

### 5. Run Redis

You need a local Redis instance. Easiest via Docker:

```bash
docker run -d -p 6379:6379 redis
```

Or run a local Redis server on `localhost:6379`.

### 6. Run database migrations

```bash
python manage.py migrate
```

### 7. Create superuser (admin)

```bash
python manage.py createsuperuser
```

### 8. Seed sample stations, trains, and a few schedules (MANDATORY once per fresh DB)

This script lives in `create_sample_data.py` and is meant to be pasted into the Django shell:

```bash
python manage.py shell
```

Then open `create_sample_data.py`, copy its entire contents, paste into the shell, and press Enter. You should see logs like:

```text
Sample data created successfully!
You can now:
1. Visit http://localhost:8000/
2. Register/Login
3. Search trains and make bookings
```

### 9. Generate rolling schedules for multiple days (optional but recommended)

The `seed_schedules` management command creates schedules per day for a range, based on predefined routes:

```bash
python manage.py seed_schedules --days 14
```

This keeps schedules available for the next 14 days using the trains seeded by `create_sample_data.py`.

### 10. Start Django server

```bash
python manage.py runserver 0.0.0.0:8000
```

Visit:

- Web UI: http://localhost:8000/
- Admin: http://localhost:8000/admin/

### 11. Start Celery worker (new terminal, same venv)

```bash
python -m celery -A config worker --loglevel=info --pool=solo
```

Celery runs the background expiry task that moves `PENDING` bookings to `EXPIRED` after the lock TTL.

---

2. Web UI Flow

---

1. Register/Login at http://localhost:8000/ (or your ngrok URL when testing webhooks)
2. Search for trains by source/destination
3. Click "Book" to create a booking
4. Add passenger details
5. View booking details
6. Complete payment
7. View all your bookings
8. Cancel bookings (if eligible)

---

3. API Authentication Flow

---

1. Register User
   POST /api/auth/register/

2. Login User
   POST /api/auth/login/

3. Use Access Token
   Authorization: Bearer <access_token>

All booking APIs require authentication.

---

3. Core System Flow

---

1. User searches trains
2. System shows real-time availability
3. User initiates booking
4. Seats are locked temporarily (Redis)
5. Booking remains PENDING
6. User simulates payment
7. On SUCCESS → booking CONFIRMED
8. On FAILURE or timeout → booking EXPIRED

---

4. Booking Lifecycle

---

```bash
PENDING
   ↓ (Payment SUCCESS)
CONFIRMED

PENDING
   ↓ (Payment FAILED)
EXPIRED

PENDING
   ↓ (15 min timeout)
EXPIRED

CONFIRMED
   ↓ (User cancels before cutoff)
CANCELLED
```

---

5. Key Design Decisions

---

- Count-based seats (no seat numbers) per schedule; availability is derived from total seats minus confirmed seats and Redis locks.
- `seed_schedules` management command to generate per-day schedules for a date range using predefined routes.
- Redis used purely for transient seat locks; source of truth for confirmed seats is the database.
- Celery task `expire_booking` owns expiry; front-end timers are informational and derived from server-side timestamps.
- Payment flow integrated with Razorpay test mode, including signature verification and a webhook for robust confirmation.

---

6. Razorpay + ngrok (local webhook testing)

---

- Start server: `python manage.py runserver 0.0.0.0:8000`
- Start tunnel: `ngrok http 8000` → use the HTTPS URL it prints
- Set env in `.env` (test keys + webhook secret):
  - `RAZORPAY_KEY_ID=...`
  - `RAZORPAY_KEY_SECRET=...`
  - `RAZORPAY_WEBHOOK_SECRET=...`
- In Razorpay Dashboard (Test mode):
  - Webhook URL: `<your-ngrok-https>/api/bookings/razorpay/webhook/`
  - Secret: same as `RAZORPAY_WEBHOOK_SECRET`
  - Events: check `payment.captured`
- Log in via the same ngrok URL (so session cookies match) before paying.
- Flow: create booking → pay via Razorpay checkout → webhook confirms booking server-side; UI verify call is optional now.

---

7. Architecture / Design Overview

---

### High-level layers

1. Presentation layer
   - Django server-rendered UI views in `apps.trains.views_ui` and `apps.bookings.views_ui`.
   - Django REST Framework APIs in `apps.trains.views`, `apps.bookings.views`, `apps.core.views`.

2. Service layer
   - Core booking logic (seat locking, payment processing, cancellation) in `apps.bookings.services`.

3. Data layer
   - Django ORM over SQLite (or any configured DB) with models:
     - `Station`, `Train`, `Schedule` in `apps.trains.models`.
     - `Booking`, `Passenger` in `apps.bookings.models`.

4. Caching / locking layer
   - Redis client in `apps.core.redis_client`.
   - Keys: `seat_lock:<schedule_id>` store locked seat counts.

5. Background worker layer
   - Celery app in `config.celery`.
   - Task `expire_booking` in `apps.bookings.tasks` handles automatic expiry.

### Booking and seat-availability model

- Each `Schedule` has `total_seats`.
- Confirmed seats are derived from `Booking` rows with `status=CONFIRMED`.
- Pending locks are stored in Redis via `lock_seats` in `apps.bookings.services`.

Formula:

```text
available_seats = total_seats - confirmed_seats - locked_seats
```

This keeps confirmed data strongly consistent in the DB while using Redis for fast, concurrent seat locking.

### Concurrency and race-condition handling

- Seat locking:
  - Uses atomic `INCRBY` in Redis (`lock_seats`).
  - If `confirmed + locked` exceeds `total_seats`, it rolls back the lock with `DECRBY` and rejects the booking.

- Booking expiry:
  - Each new booking schedules a Celery task `expire_booking(booking_id)` with `LOCK_TTL` seconds.
  - The task uses `select_for_update()` to lock the booking row and only expires bookings still `PENDING`.
  - It also uses a Redis idempotency key `expire_task_executed:<booking_id>` to ensure only one worker executes the expiry logic.

- Payment processing:
  - `process_payment` in `apps.bookings.services` runs in a DB transaction, locking the booking row with `select_for_update()`.
  - If already `CONFIRMED`, it returns early and does not touch Redis again.
  - If `EXPIRED` or `CANCELLED`, it rejects payment as ineligible.
  - On `SUCCESS`, it:
    - Sets `status=CONFIRMED`,
    - Updates all passengers to `CONFIRMED`,
    - Decrements Redis by `locked_seats_count` for that schedule.

### Payment and Razorpay integration

- Order creation:
  - `create_razorpay_order(booking)` creates an order with `amount` (₹500 per passenger), `currency=INR`, and `receipt=str(booking.id)`.

- UI payment flow:
  - `bookings/payment.html` uses Razorpay Checkout JS to open the payment popup.
  - On success, it posts `order_id`, `payment_id`, and `signature` to `/api/bookings/<booking_id>/verify-payment/`.
  - `verify_payment_api` verifies the signature and calls `process_payment`.
  - If the webhook already confirmed the booking, this endpoint returns success idempotently.

- Webhook flow (recommended for robustness):
  - Endpoint: `/api/bookings/razorpay/webhook/`.
  - Verifies `X-Razorpay-Signature` using `RAZORPAY_WEBHOOK_SECRET`.
  - On `payment.captured`, it fetches the Razorpay order, reads `receipt` (booking id), and calls `process_payment(booking_id, "SUCCESS")`.
  - Safe to receive duplicates; idempotency in `process_payment` prevents double processing.

---

8. Assumptions

---

- Single class of travel; all seats are homogeneous and count-based (no berth/coach-level allocation).
- Flat fare of ₹500 per passenger (configurable via `FARE_PER_PASSENGER` in `apps.bookings.services`).
- Booking cutoff is 2 hours before departure; cancellations are not allowed after that cutoff.
- Payments are handled via Razorpay test environment; no real money is involved.
- One user account represents a single customer.


These simplify the model while focusing on seat locking, race conditions, and booking lifecycle correctness.
