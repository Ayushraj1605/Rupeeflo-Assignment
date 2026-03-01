# Railway Booking System

A backend for booking train tickets. Users can search trains, book seats, pay via Razorpay, cancel bookings, and get automatic refunds. Built with Django, Redis for seat locking, and Celery for background expiry.

---

## Getting Started

### Prerequisites

- Python 3.10+
- Redis running on `localhost:6379`
- A free [Razorpay](https://razorpay.com) test account

### 1. Clone and set up

```bash
git clone https://github.com/Ayushraj1605/Rupeeflo-Assignment.git
cd railway-booking-system
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Create your `.env` file

Create a `.env` file in the root of the project:

```env
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_secret_here
RAZORPAY_WEBHOOK_SECRET=any_string_you_choose
```

Get these from your Razorpay dashboard under **Settings → API Keys** (make sure you are in Test Mode).

### 3. Start Redis

```bash
docker run -d -p 6379:6379 redis
```

### 4. Run migrations and create an admin user

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Seed train data

This only needs to be done once on a fresh database.

```bash
python manage.py shell
```

Copy the contents of `create_sample_data.py` and paste it into the shell. You will see a success message once done.

### 6. Generate schedules (optional but recommended)

```bash
python manage.py seed_schedules --days 14
```

This creates bookable schedules for the next 14 days.

### 7. Start the server

```bash
python manage.py runserver
```

- Web UI: http://localhost:8000
- Admin panel: http://localhost:8000/admin

### 8. Start the Celery worker (separate terminal)

```bash
python -m celery -A config worker --loglevel=info --pool=solo
```

This handles automatic booking expiry after 15 minutes.

---

## How It Works

### Booking flow

1. User searches for trains by source, destination, and date
2. User creates a booking — seats are locked in Redis immediately
3. Booking stays `PENDING` for 15 minutes while the user pays
4. On successful payment → booking moves to `CONFIRMED`
5. On payment failure or timeout → booking moves to `EXPIRED`, seats are released

### Booking states

```
PENDING   →  CONFIRMED      (payment succeeded)
PENDING   →  PAYMENT_FAILED
PENDING   →  EXPIRED        (15 min timeout via Celery)
CONFIRMED →  CANCELLED      (user cancels before cutoff, refund auto-triggered)
```

### Seat availability

No individual seat numbers. Availability is computed as:

```
available = total_seats - confirmed_seats (DB) - locked_seats (Redis)
```

Redis handles fast concurrent locking. The database is the source of truth for confirmed seats.

---

## Testing Payments Locally

You need ngrok to receive Razorpay webhooks on localhost:

```bash
ngrok http 8000
```

In the Razorpay dashboard (Test Mode) under **Settings → Webhooks**:

- URL: `https://<your-ngrok-subdomain>.ngrok-free.app/api/payments/webhook/razorpay/`
- Secret: same value as `RAZORPAY_WEBHOOK_SECRET` in your `.env`
- Events: `payment.captured`, `refund.processed`, `refund.failed`

Use test card `4111 1111 1111 1111` with any future expiry and any CVV. No real money is charged.

---

## Project Structure

```
apps/
  bookings/     booking lifecycle, passengers, RBAC
  payments/     Razorpay integration, refunds
  trains/       train search, schedules
  core/         auth (register), Redis client
config/         Django settings, Celery, URLs
templates/      server-rendered UI
```

---

## Assumptions

- Flat fare of ₹500 per passenger
- Booking cutoff is 2 hours before departure — no cancellations after that
- Count-based seats only, no berth or coach allocation
- One account per customer
- All payments run through Razorpay test environment
