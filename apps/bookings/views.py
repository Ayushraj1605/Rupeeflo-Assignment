from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import razorpay
from .services import (
    create_booking,
    cancel_booking,
    process_payment,
    create_razorpay_order,
    verify_razorpay_signature,
)
from .models import Booking, BookingStatus


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_booking_api(request):
    user = request.user
    schedule_id = request.data.get("schedule_id")
    passengers = request.data.get("passengers", [])

    if not passengers:
        return Response({"error": "Passenger list required"}, status=400)

    booking, message = create_booking(user, schedule_id, passengers)

    if booking is None:
        return Response({"error": message}, status=400)

    passenger_data = [
        {
            "name": p.name,
            "age": p.age,
            "status": p.status
        }
        for p in booking.passengers.all()
    ]

    return Response({
        "booking_id": booking.id,
        "status": booking.status,
        "passengers": passenger_data,
        "message": message
    })



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_booking_api(request):
    booking_id = request.data.get("booking_id")

    booking, message = cancel_booking(booking_id)

    if booking is None:
        return Response({"error": message}, status=400)

    return Response({
        "booking_id": booking.id,
        "status": booking.status,
        "message": message
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def booking_status_api(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=404)

    return Response({
        "booking_id": booking.id,
        "status": booking.status
    })



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_booking_api(request):
    booking_id = request.data.get("booking_id")
    payment_status = request.data.get("payment_status")

    if payment_status not in ["SUCCESS", "FAILED"]:
        return Response({"error": "Invalid payment status"}, status=400)

    booking, message = process_payment(booking_id, payment_status)

    if booking is None:
        return Response({"error": message}, status=400)

    return Response({
        "booking_id": booking.id,
        "status": booking.status,
        "message": message
    })



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def booking_detail_api(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=404)

    passengers = [
        {
            "name": p.name,
            "age": p.age,
            "status": p.status
        }
        for p in booking.passengers.all()
    ]

    return Response({
        "booking_id": booking.id,
        "status": booking.status,
        "schedule_id": booking.schedule_id,
        "passengers": passengers,
        "created_at": booking.created_at
    })
    
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_user_bookings(request):
    user_id = request.GET.get("user_id")

    if not user_id:
        return Response({"error": "user_id required"}, status=400)

    bookings = Booking.objects.filter(user_id=user_id).order_by("-created_at")

    data = []

    for booking in bookings:
        data.append({
            "booking_id": booking.id,
            "status": booking.status,
            "schedule_id": booking.schedule_id,
            "passenger_count": booking.passenger_count,
            "created_at": booking.created_at
        })

    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_order_api(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if booking.status != BookingStatus.PENDING:
        return Response({"error": "Booking is not pending"}, status=400)
    order = create_razorpay_order(booking)
    return Response({
        "order_id": order["id"],
        "key_id": settings.RAZORPAY_KEY_ID,
        "amount": order["amount"],
        "currency": order["currency"],
    })


@csrf_exempt
@api_view(['POST'])
@authentication_classes([SessionAuthentication, JWTAuthentication])
@permission_classes([AllowAny])
def verify_payment_api(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.status == BookingStatus.CONFIRMED:
        return Response({"status": booking.status, "message": "Payment already verified"})

    if booking.status != BookingStatus.PENDING:
        return Response({"error": "Booking is not eligible for payment"}, status=400)

    order_id = request.data.get("order_id")
    payment_id = request.data.get("payment_id")
    signature = request.data.get("signature")

    if not all([order_id, payment_id, signature]):
        return Response({"error": "Missing payment parameters"}, status=400)

    verify_razorpay_signature(order_id, payment_id, signature)

    booking, message = process_payment(booking_id, "SUCCESS")
    if booking is None:
        return Response({"error": message}, status=400)

    return Response({"status": booking.status, "message": "Payment verified"})


@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def razorpay_webhook_api(request):
    """Handle Razorpay webhook events to confirm payments server-side."""

    signature = request.headers.get("X-Razorpay-Signature")
    if not signature:
        return Response({"error": "Missing signature"}, status=400)

    body = request.body.decode("utf-8")
    try:
        razorpay.Utility().verify_webhook_signature(
            body=body,
            signature=signature,
            secret=settings.RAZORPAY_WEBHOOK_SECRET,
        )
    except razorpay.errors.SignatureVerificationError:
        return Response({"error": "Invalid signature"}, status=400)

    payload = request.data
    event = payload.get("event")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment_entity.get("order_id")
    status = payment_entity.get("status")

    if event == "payment.captured" and order_id and status == "captured":
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order = client.order.fetch(order_id)
            receipt = order.get("receipt")
            booking_id = int(receipt)
        except Exception:
            return Response({"error": "Could not resolve booking from order"}, status=400)

        booking, message = process_payment(booking_id, "SUCCESS")
        return Response({"status": booking.status if booking else None, "message": message}, status=200)

    return Response({"status": "ignored"}, status=200)
