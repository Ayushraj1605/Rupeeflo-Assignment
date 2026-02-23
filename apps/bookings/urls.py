from django.urls import path
from .views import (
    create_booking_api,
    cancel_booking_api,
    booking_status_api,
    pay_booking_api,
    booking_detail_api,
    list_user_bookings,
    create_payment_order_api,
    verify_payment_api,
    razorpay_webhook_api,
)


urlpatterns = [
    path("create/", create_booking_api, name="create_booking_api"),
    path("cancel/", cancel_booking_api, name="cancel_booking_api"),
    path("status/<int:booking_id>/", booking_status_api, name="booking_status_api"),
    path("pay/", pay_booking_api, name="pay_booking_api"),
    path("detail/<int:booking_id>/", booking_detail_api, name="booking_detail_api"),
    path("my-bookings/", list_user_bookings, name="list_user_bookings"),
    path("<int:booking_id>/payment-order/", create_payment_order_api, name="create_payment_order_api"),
    path("<int:booking_id>/verify-payment/", verify_payment_api, name="verify_payment_api"),
    path("razorpay/webhook/", razorpay_webhook_api, name="razorpay_webhook_api"),
]
