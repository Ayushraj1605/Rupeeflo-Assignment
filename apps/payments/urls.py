from django.urls import path
from .views import (
    create_payment_order_api,
    verify_payment_api,
    razorpay_webhook_api,
    refund_booking_api,
)

urlpatterns = [
    path("<int:booking_id>/order/", create_payment_order_api, name="create_payment_order_api"),
    path("<int:booking_id>/verify/", verify_payment_api, name="verify_payment_api"),
    path("<int:booking_id>/refund/", refund_booking_api, name="refund_booking_api"),
    path("webhook/razorpay/", razorpay_webhook_api, name="razorpay_webhook_api"),
]
