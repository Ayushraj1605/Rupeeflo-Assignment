# API Reference

Base URL: `http://localhost:8000`

All endpoints that require authentication expect a JWT Bearer token in the header:

```
Authorization: Bearer <access_token>
```

Get a token by logging in via `POST /api/auth/login/`.

---

## Auth

### Register
`POST /api/auth/register/`

No authentication required.

**Request**
```json
{
  "username": "john",
  "password": "secret123",
  "email": "john@example.com"
}
```

**Response `201`**
```json
{
  "message": "User registered successfully"
}
```

---

### Login
`POST /api/auth/login/`

No authentication required.

**Request**
```json
{
  "username": "john",
  "password": "secret123"
}
```

**Response `200`**
```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>"
}
```

---

### Refresh Token
`POST /api/auth/refresh/`

**Request**
```json
{
  "refresh": "<jwt_refresh_token>"
}
```

**Response `200`**
```json
{
  "access": "<new_jwt_access_token>"
}
```

---

## Trains

### Search Trains
`GET /api/trains/search/`

No authentication required. All query params are optional — omitting them returns all schedules.

**Query params**

| Param | Type | Example |
|---|---|---|
| `source` | string | `NDLS` |
| `destination` | string | `MMCT` |
| `travel_date` | YYYY-MM-DD | `2026-03-15` |

**Response `200`**
```json
[
  {
    "schedule_id": 1,
    "train": "Rajdhani Express",
    "train_number": "12301",
    "source": "NDLS",
    "destination": "MMCT",
    "travel_date": "2026-03-15",
    "departure_time": "16:00:00",
    "available_seats": 42
  }
]
```

---

## Bookings

### Create Booking
`POST /api/bookings/create/`

Locks seats in Redis immediately. Booking expires in 15 minutes if payment is not completed.

**Request**
```json
{
  "schedule_id": 1,
  "passengers": [
    { "name": "John Doe", "age": 28 },
    { "name": "Jane Doe", "age": 25 }
  ]
}
```

**Response `200`**
```json
{
  "booking_id": 7,
  "status": "PENDING",
  "passengers": [
    { "name": "John Doe", "age": 28, "status": "PENDING" },
    { "name": "Jane Doe", "age": 25, "status": "PENDING" }
  ],
  "message": "Booking initiated"
}
```

**Errors**

| Status | Reason |
|---|---|
| `400` | No passengers provided |
| `400` | Not enough seats available |
| `400` | Booking cutoff has passed |

---

### Get My Bookings
`GET /api/bookings/my-bookings/`

Returns all bookings for the logged-in user.

**Response `200`**
```json
[
  {
    "booking_id": 7,
    "status": "CONFIRMED",
    "schedule_id": 1,
    "passenger_count": 2,
    "created_at": "2026-03-01T10:00:00Z"
  }
]
```

---

### Booking Detail
`GET /api/bookings/detail/<booking_id>/`

Only the owner of the booking can access this.

**Response `200`**
```json
{
  "booking_id": 7,
  "status": "CONFIRMED",
  "schedule_id": 1,
  "passengers": [
    { "name": "John Doe", "age": 28, "status": "CONFIRMED" }
  ],
  "created_at": "2026-03-01T10:00:00Z"
}
```

**Errors**

| Status | Reason |
|---|---|
| `404` | Booking not found or does not belong to the user |

---

### Booking Status
`GET /api/bookings/status/<booking_id>/`

Lightweight status check. Only accessible by the booking owner.

**Response `200`**
```json
{
  "booking_id": 7,
  "status": "CONFIRMED",
  "message": ""
}
```

---

### Cancel Booking
`POST /api/bookings/cancel/`

Only the owner can cancel. If the booking was `CONFIRMED` and had a payment, a refund is automatically triggered.

**Request**
```json
{
  "booking_id": 7
}
```

**Response `200`**
```json
{
  "booking_id": 7,
  "status": "CANCELLED",
  "message": "Booking cancelled successfully. Refund initiated successfully"
}
```

If refund fails, the booking is still cancelled but the message will include the reason:

```json
{
  "booking_id": 7,
  "status": "CANCELLED",
  "message": "Booking cancelled successfully. Refund could not be initiated: No payment record found for this booking"
}
```

**Errors**

| Status | Reason |
|---|---|
| `404` | Booking not found or does not belong to the user |
| `400` | Booking already inactive |
| `400` | Cancellation window closed (past cutoff) |

---

### Admin — List All Bookings
`GET /api/bookings/admin/all/`

Requires `is_staff = True`.

**Response `200`** — same shape as "Get My Bookings" but contains all users' bookings.

---

### Admin — Booking Detail
`GET /api/bookings/admin/<booking_id>/detail/`

Requires `is_staff = True`. Returns full detail for any booking regardless of owner.

---

## Payments

### Create Payment Order
`POST /api/payments/<booking_id>/order/`

Creates a Razorpay order for the booking. Booking must be in `PENDING` status. Use the returned `order_id` and `key_id` to open the Razorpay checkout popup on the frontend.

**Response `200`**
```json
{
  "order_id": "order_AbCd1234",
  "key_id": "rzp_test_xxxx",
  "amount": 100000,
  "currency": "INR"
}
```

Amount is in **paise** (₹500 per passenger × 100).

**Errors**

| Status | Reason |
|---|---|
| `404` | Booking not found or not owned by the user |
| `400` | Booking is not in PENDING status |

---

### Verify Payment
`POST /api/payments/<booking_id>/verify/`

Call this after the Razorpay checkout succeeds on the frontend. Verifies the signature and confirms the booking.

**Request**
```json
{
  "order_id": "order_AbCd1234",
  "payment_id": "pay_XyZ9876",
  "signature": "<razorpay_signature>"
}
```

**Response `200`**
```json
{
  "status": "CONFIRMED",
  "message": "Payment verified"
}
```

If the booking was already confirmed via webhook, this returns success idempotently.

**Errors**

| Status | Reason |
|---|---|
| `400` | Missing payment parameters |
| `400` | Booking not eligible for payment |
| `400` | Signature verification failed |

---

### Refund Booking
`POST /api/payments/<booking_id>/refund/`

Manually trigger a refund. The booking must already be `CANCELLED` and a `Payment` record must exist (i.e. the booking was paid through Razorpay).

Refunds are also triggered automatically when you call `POST /api/bookings/cancel/` on a `CONFIRMED` booking.

**Request**
```json
{
  "reason": "customer request"
}
```

`reason` is optional and defaults to `"cancellation"`.

**Response `200`**
```json
{
  "refund_id": 1,
  "razorpay_refund_id": "rfnd_AbCd1234",
  "amount_paise": 100000,
  "status": "PROCESSED",
  "reason": "customer request",
  "message": "Refund initiated successfully"
}
```

**Errors**

| Status | Reason |
|---|---|
| `404` | Booking not found or not owned by the user |
| `400` | Booking is not cancelled |
| `400` | No payment record found |
| `400` | Already refunded |
| `400` | Razorpay refund API error |

---

### Razorpay Webhook
`POST /api/payments/webhook/razorpay/`

Handles events sent by Razorpay. Do not call this manually — it is for Razorpay's servers only.

Requires `X-Razorpay-Signature` header.

**Handled events**

| Event | Action |
|---|---|
| `payment.captured` | Confirms the booking and creates a `Payment` record |
| `refund.processed` | Updates the `Refund` record status to `PROCESSED` |
| `refund.failed` | Updates the `Refund` record status to `FAILED` |

Any other event returns `{"status": "ignored"}`.

---

## Error format

All errors follow this shape:

```json
{
  "error": "Human readable message"
}
```

Validation errors from serializers return field-level detail:

```json
{
  "passengers": ["This field is required."]
}
```
