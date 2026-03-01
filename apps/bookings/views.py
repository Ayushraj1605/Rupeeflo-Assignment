from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .services import (
    create_booking,
    cancel_booking,
)
from .models import Booking
from .serializers import (
    BookingCreateSerializer,
    BookingResponseSerializer,
    BookingStatusSerializer,
    BookingDetailSerializer,
    BookingListItemSerializer,
    PassengerResponseSerializer,
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_booking_api(request):
    serializer = BookingCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    validated = serializer.validated_data
    booking, message = create_booking(
        request.user,
        validated["schedule_id"],
        validated["passengers"],
    )

    if booking is None:
        return Response({"error": message}, status=400)

    passengers = PassengerResponseSerializer(
        booking.passengers.all(), many=True
    ).data

    response = BookingResponseSerializer({
        "booking_id": booking.id,
        "status": booking.status,
        "passengers": passengers,
        "message": message,
    })
    return Response(response.data)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_booking_api(request):
    booking_id = request.data.get("booking_id")
    booking, message = cancel_booking(booking_id)

    if booking is None:
        return Response({"error": message}, status=400)

    response = BookingStatusSerializer({
        "booking_id": booking.id,
        "status": booking.status,
        "message": message,
    })
    return Response(response.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def booking_status_api(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=404)

    response = BookingStatusSerializer({
        "booking_id": booking.id,
        "status": booking.status,
        "message": "",
    })
    return Response(response.data)





@api_view(['GET'])
@permission_classes([IsAuthenticated])
def booking_detail_api(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=404)

    passengers = PassengerResponseSerializer(
        booking.passengers.all(), many=True
    ).data

    response = BookingDetailSerializer({
        "booking_id": booking.id,
        "status": booking.status,
        "schedule_id": booking.schedule_id,
        "passengers": passengers,
        "created_at": booking.created_at,
    })
    return Response(response.data)
    
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_user_bookings(request):
    user_id = request.GET.get("user_id")

    if not user_id:
        return Response({"error": "user_id required"}, status=400)

    bookings = Booking.objects.filter(user_id=user_id).order_by("-created_at")

    response = BookingListItemSerializer(
        [
            {
                "booking_id": b.id,
                "status": b.status,
                "schedule_id": b.schedule_id,
                "passenger_count": b.passenger_count,
                "created_at": b.created_at,
            }
            for b in bookings
        ],
        many=True,
    )
    return Response(response.data)