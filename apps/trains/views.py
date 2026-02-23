from datetime import date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Sum
from apps.bookings.models import Booking, BookingStatus
from apps.core.redis_client import redis_client
from .models import Schedule


@api_view(['GET'])
@permission_classes([AllowAny])
def search_trains(request):
    source = request.GET.get("source")
    destination = request.GET.get("destination")
    travel_date = request.GET.get("travel_date")

    schedules = Schedule.objects.select_related(
        "train", "source_station", "destination_station"
    ).all()

    if source:
        schedules = schedules.filter(source_station__code__iexact=source)

    if destination:
        schedules = schedules.filter(destination_station__code__iexact=destination)

    if travel_date:
        try:
            parsed_date = date.fromisoformat(travel_date)
        except ValueError:
            return Response({"error": "Invalid travel_date. Use YYYY-MM-DD."}, status=400)
        schedules = schedules.filter(travel_date=parsed_date)

    data = []

    for schedule in schedules:

        confirmed_seats = Booking.objects.filter(
            schedule_id=schedule.id,
            status=BookingStatus.CONFIRMED
        ).aggregate(total=Sum("passenger_count"))["total"] or 0

        locked_seats = redis_client.get(f"seat_lock:{schedule.id}")
        locked_seats = int(locked_seats) if locked_seats else 0

        available_seats = schedule.total_seats - confirmed_seats - locked_seats

        data.append({
            "schedule_id": schedule.id,
            "train": schedule.train.name,
            "train_number": schedule.train.train_number,
            "source": schedule.source_station.code,
            "destination": schedule.destination_station.code,
            "travel_date": schedule.travel_date,
            "departure_time": schedule.departure_time,
            "available_seats": available_seats
        })

    return Response(data)
