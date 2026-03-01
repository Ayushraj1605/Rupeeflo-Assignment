from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
import razorpay
from apps.bookings.models import Booking, BookingStatus
from .models import Refund, RefundStatus
from .serializers import (
    CreatePaymentOrderResponseSerializer,
    VerifyPaymentRequestSerializer,
    PaymentStatusResponseSerializer,
    RefundRequestSerializer,
    RefundResponseSerializer,
)
from .services import (
    create_razorpay_order,
    verify_razorpay_signature,
    process_payment,
    initiate_refund,
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_order_api(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if booking.status != BookingStatus.PENDING:
        return Response({"error": "Booking is not pending"}, status=400)
    order = create_razorpay_order(booking)
    serializer = CreatePaymentOrderResponseSerializer({
        "order_id": order["id"],
        "key_id": settings.RAZORPAY_KEY_ID,
        "amount": order["amount"],
        "currency": order["currency"],
    })
    return Response(serializer.data)


@csrf_exempt
@api_view(['POST'])
@authentication_classes([SessionAuthentication, JWTAuthentication])
@permission_classes([AllowAny])
def verify_payment_api(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.status == BookingStatus.CONFIRMED:
        serializer = PaymentStatusResponseSerializer({
            "status": booking.status,
            "message": "Payment already verified",
        })
        return Response(serializer.data)

    if booking.status != BookingStatus.PENDING:
        return Response({"error": "Booking is not eligible for payment"}, status=400)

    input_serializer = VerifyPaymentRequestSerializer(data=request.data)
    if not input_serializer.is_valid():
        return Response(input_serializer.errors, status=400)

    validated = input_serializer.validated_data
    verify_razorpay_signature(
        validated["order_id"],
        validated["payment_id"],
        validated["signature"],
    )

    booking, message = process_payment(
        booking_id,
        "SUCCESS",
        razorpay_payment_id=validated["payment_id"],
        razorpay_order_id=validated["order_id"],
    )
    if booking is None:
        return Response({"error": message}, status=400)

    serializer = PaymentStatusResponseSerializer({
        "status": booking.status,
        "message": "Payment verified",
    })
    return Response(serializer.data)


@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def razorpay_webhook_api(request):
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

        payment_id = payment_entity.get("id")
        booking, message = process_payment(
            booking_id,
            "SUCCESS",
            razorpay_payment_id=payment_id,
            razorpay_order_id=order_id,
        )
        serializer = PaymentStatusResponseSerializer({
            "status": booking.status if booking else None,
            "message": message,
        })
        return Response(serializer.data, status=200)

    if event in ("refund.processed", "refund.failed"):
        refund_entity = payload.get("payload", {}).get("refund", {}).get("entity", {})
        razorpay_refund_id = refund_entity.get("id")
        if razorpay_refund_id:
            new_status = RefundStatus.PROCESSED if event == "refund.processed" else RefundStatus.FAILED
            Refund.objects.filter(razorpay_refund_id=razorpay_refund_id).update(status=new_status)
        return Response({"status": "ok"}, status=200)

    return Response({"status": "ignored"}, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refund_booking_api(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status != BookingStatus.CANCELLED:
        return Response({"error": "Only cancelled bookings are eligible for refund"}, status=400)

    input_serializer = RefundRequestSerializer(data=request.data)
    if not input_serializer.is_valid():
        return Response(input_serializer.errors, status=400)

    refund, message = initiate_refund(
        booking_id,
        reason=input_serializer.validated_data["reason"],
    )

    if refund is None:
        return Response({"error": message}, status=400)

    serializer = RefundResponseSerializer({
        "refund_id": refund.id,
        "razorpay_refund_id": refund.razorpay_refund_id,
        "amount_paise": refund.amount_paise,
        "status": refund.status,
        "reason": refund.reason,
        "message": message,
    })
    return Response(serializer.data)
