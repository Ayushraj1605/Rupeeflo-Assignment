from celery import shared_task
from django.utils import timezone
from .models import Booking, BookingStatus
from apps.core.redis_client import redis_client
from django.db import transaction

@shared_task
def expire_booking(booking_id):
    
    print(f"[EXPIRE_BOOKING] Task started for booking_id={booking_id}")
    
    idempotency_key = f"expire_task_executed:{booking_id}"
    acquired = redis_client.set(idempotency_key, "1", nx=True, ex=3600)
    if not acquired:
        print(f"[EXPIRE_BOOKING] Task already acquired by another worker for booking {booking_id}, skipping")
        return
    
    print(f"[EXPIRE_BOOKING] Acquired idempotency lock for booking {booking_id}")
    
    with transaction.atomic():
        try:
            booking = Booking.objects.select_for_update().get(id=booking_id)
            print(f"[EXPIRE_BOOKING] Acquired DB lock for booking {booking_id}, status={booking.status}")
        except Booking.DoesNotExist:
            print(f"[EXPIRE_BOOKING] Booking {booking_id} not found")
            return

        if booking.status != BookingStatus.PENDING:
            print(f"[EXPIRE_BOOKING] Booking {booking_id} already processed (status={booking.status}), skipping")
            return
        
        booking.status = BookingStatus.EXPIRED
        booking.save()
        print(f"[EXPIRE_BOOKING] Updated booking {booking_id} to EXPIRED")

        booking.passengers.all().update(status="EXPIRED")

        redis_client.decrby(
            f"seat_lock:{booking.schedule_id}",
            booking.locked_seats_count
        )
        print(f"[EXPIRE_BOOKING] Decremented Redis by {booking.locked_seats_count} for schedule {booking.schedule_id}")
