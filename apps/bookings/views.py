from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from .services import (
    create_booking,
    cancel_booking,
)
from .models import Booking, BookingStatus
from .serializers import (
    BookingCreateSerializer,
    BookingResponseSerializer,
    BookingStatusSerializer,
    BookingDetailSerializer,
    BookingListItemSerializer,
    PassengerResponseSerializer,
)
from apps.payments.services import initiate_refund


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

    try:
        booking_before = Booking.objects.get(id=booking_id, user=request.user)
        was_confirmed = booking_before.status == BookingStatus.CONFIRMED
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found or access denied"}, status=404)

    booking, message = cancel_booking(booking_id)

    if booking is None:
        return Response({"error": message}, status=400)

    refund_initiated = False
    refund_message = None
    if was_confirmed:
        refund, refund_message = initiate_refund(booking_id)
        refund_initiated = refund is not None

    final_message = message
    if was_confirmed:
        if refund_initiated:
            final_message = f"{message}. {refund_message}"
        else:
            final_message = f"{message}. Refund could not be initiated: {refund_message}"

    response = BookingStatusSerializer({
        "booking_id": booking.id,
        "status": booking.status,
        "message": final_message,
    })
    return Response(response.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def booking_status_api(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id, user=request.user)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found or access denied"}, status=404)

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
        booking = Booking.objects.get(id=booking_id, user=request.user)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found or access denied"}, status=404)

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
    bookings = Booking.objects.filter(user=request.user).order_by("-created_at")

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


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_list_all_bookings(request):
    bookings = Booking.objects.all().order_by("-created_at")

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


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_booking_detail(request, booking_id):
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