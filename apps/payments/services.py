from django.conf import settings
from django.db import transaction
from django.utils import timezone
import razorpay
from apps.core.redis_client import redis_client
from apps.bookings.models import Booking, BookingStatus
from .models import Payment, PaymentStatus, Refund, RefundStatus

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


def process_payment(booking_id, payment_status, razorpay_payment_id=None, razorpay_order_id=None):
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

            if razorpay_payment_id and razorpay_order_id:
                Payment.objects.get_or_create(
                    booking=booking,
                    defaults={
                        "razorpay_order_id": razorpay_order_id,
                        "razorpay_payment_id": razorpay_payment_id,
                        "amount_paise": calculate_amount_paise(booking),
                        "status": PaymentStatus.SUCCESS,
                    },
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


def initiate_refund(booking_id, reason="cancellation"):
    with transaction.atomic():
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return None, "Booking not found"

        try:
            payment = Payment.objects.select_for_update().get(booking=booking)
        except Payment.DoesNotExist:
            return None, "No payment record found for this booking"

        if payment.status == PaymentStatus.REFUNDED:
            return None, "Already refunded"

        if payment.status not in [PaymentStatus.SUCCESS, PaymentStatus.PARTIALLY_REFUNDED]:
            return None, "Payment is not in a refundable state"

        client = _razorpay_client()
        try:
            refund_response = client.payment.refund(
                payment.razorpay_payment_id,
                {"amount": payment.amount_paise},
            )
        except razorpay.errors.BadRequestError as e:
            return None, f"Razorpay refund failed: {str(e)}"

        refund = Refund.objects.create(
            payment=payment,
            razorpay_refund_id=refund_response.get("id", ""),
            amount_paise=payment.amount_paise,
            status=RefundStatus.PROCESSED,
            reason=reason,
        )

        payment.status = PaymentStatus.REFUNDED
        payment.save()

        return refund, "Refund initiated successfully"
