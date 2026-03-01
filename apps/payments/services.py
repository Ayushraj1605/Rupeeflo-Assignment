from django.conf import settings
from django.db import transaction
from django.utils import timezone
import razorpay
from apps.core.redis_client import redis_client
from apps.bookings.models import Booking, BookingStatus

FARE_PER_PASSENGER = 500


def _razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def calculate_amount_paise(booking: Booking) -> int:
    return max(1, booking.passenger_count * FARE_PER_PASSENGER * 100)


def create_razorpay_order(booking: Booking):
    amount = calculate_amount_paise(booking)
    client = _razorpay_client()
    order = client.order.create(
        dict(
            amount=amount,
            currency="INR",
            receipt=str(booking.id),
            payment_capture=1,
        )
    )
    return order


def verify_razorpay_signature(order_id: str, payment_id: str, signature: str):
    client = _razorpay_client()
    client.utility.verify_payment_signature(
        {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }
    )


def process_payment(booking_id, payment_status):
    with transaction.atomic():
        try:
            booking = Booking.objects.select_for_update().get(id=booking_id)
        except Booking.DoesNotExist:
            return None, "Invalid booking"

        if booking.status == BookingStatus.CONFIRMED:
            return booking, "Booking already confirmed"

        if booking.status in [
            BookingStatus.EXPIRED,
            BookingStatus.CANCELLED,
            BookingStatus.PAYMENT_FAILED,
        ]:
            return None, "Booking not eligible for payment"

        if payment_status == "SUCCESS":
            booking.status = BookingStatus.CONFIRMED
            booking.confirmed_at = timezone.now()
            booking.save()

            booking.passengers.all().update(status="CONFIRMED")

            redis_client.decrby(
                f"seat_lock:{booking.schedule_id}",
                booking.locked_seats_count
            )

            return booking, "Payment successful. Booking confirmed."

        else:
            booking.status = BookingStatus.PAYMENT_FAILED
            booking.save()

            booking.passengers.all().update(status="EXPIRED")

            redis_client.decrby(
                f"seat_lock:{booking.schedule_id}",
                booking.locked_seats_count
            )

            return booking, "Payment failed. Booking expired."
