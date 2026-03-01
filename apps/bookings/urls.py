from django.urls import path
from .views import (
    create_booking_api,
    cancel_booking_api,
    booking_status_api,
    booking_detail_api,
    list_user_bookings,
)


urlpatterns = [
    path("create/", create_booking_api, name="create_booking_api"),
    path("cancel/", cancel_booking_api, name="cancel_booking_api"),
    path("status/<int:booking_id>/", booking_status_api, name="booking_status_api"),
    path("detail/<int:booking_id>/", booking_detail_api, name="booking_detail_api"),
    path("my-bookings/", list_user_bookings, name="list_user_bookings"),
]
