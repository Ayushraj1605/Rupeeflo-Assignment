from django.db import models, transaction
from django.utils import timezone
from apps.core.redis_client import redis_client
from apps.trains.models import Schedule
from .models import Booking, BookingStatus
from .tasks import expire_booking
from .models import Passenger


LOCK_TTL = 900

def get_available_seats(schedule_id):
    try:
        schedule = Schedule.objects.get(id=schedule_id)
    except Schedule.DoesNotExist:
        return None, "Schedule not found"

    confirmed_seats = Booking.objects.filter(
        schedule_id=schedule_id,
        status="CONFIRMED"
    ).aggregate(total=models.Sum("passenger_count"))["total"] or 0

    locked_seats = redis_client.get(f"seat_lock:{schedule_id}")
    locked_seats = int(locked_seats) if locked_seats else 0

    return schedule.total_seats - confirmed_seats - locked_seats

def lock_seats(schedule_id, seats_to_lock):
    key = f"seat_lock:{schedule_id}"
    
    new_total = redis_client.incrby(key, seats_to_lock)

    return new_total



def create_booking(user, schedule_id, passengers):

    schedule = Schedule.objects.get(id=schedule_id)

    if timezone.now() >= schedule.booking_cutoff_time:
        return None, "Booking closed for this train"

    passenger_count = len(passengers)

    if passenger_count == 0:
        return None, "At least one passenger required"

    confirmed_seats = Booking.objects.filter(
        schedule_id=schedule_id,
        status="CONFIRMED"
    ).aggregate(total=models.Sum("passenger_count"))["total"] or 0

    new_locked_total = lock_seats(schedule_id, passenger_count)

    if confirmed_seats + new_locked_total > schedule.total_seats:
        redis_client.decrby(f"seat_lock:{schedule_id}", passenger_count)
        return None, "Not enough seats available"

    booking = Booking.objects.create(
        user=user,
        schedule_id=schedule_id,
        passenger_count=passenger_count,
        locked_seats_count=passenger_count,
        status=BookingStatus.PENDING
    )

    for passenger in passengers:
        Passenger.objects.create(
            booking=booking,
            name=passenger["name"],
            age=passenger["age"]
        )

    expire_booking.apply_async(
        args=[booking.id],
        countdown=LOCK_TTL,
        task_id=f"expire_booking_{booking.id}"
    )

    return booking, "Booking initiated"



def cancel_booking(booking_id):
    with transaction.atomic():
        try:
            booking = Booking.objects.select_for_update().get(id=booking_id)
        except Booking.DoesNotExist:
            return None, "Booking not found"

        if booking.status in [
            BookingStatus.CANCELLED,
            BookingStatus.EXPIRED,
            BookingStatus.PAYMENT_FAILED,
        ]:
            return None, "Booking already inactive"

        schedule = booking.schedule

        if timezone.now() >= schedule.booking_cutoff_time:
            return None, "Cancellation window closed"

        original_status = booking.status

        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.save()

        booking.passengers.all().update(status="CANCELLED")

        if original_status == BookingStatus.PENDING:
            redis_client.decrby(
                f"seat_lock:{schedule.id}",
                booking.passenger_count
            )

        return booking, "Booking cancelled successfully"