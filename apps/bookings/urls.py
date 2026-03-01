from django.urls import path
from .views import (
    create_booking_api,
    cancel_booking_api,
    booking_status_api,
    booking_detail_api,
    list_user_bookings,
    admin_list_all_bookings,
    admin_booking_detail,
)


urlpatterns = [
    path("create/", create_booking_api, name="create_booking_api"),
    path("cancel/", cancel_booking_api, name="cancel_booking_api"),
    path("status/<int:booking_id>/", booking_status_api, name="booking_status_api"),
    path("detail/<int:booking_id>/", booking_detail_api, name="booking_detail_api"),
    path("my-bookings/", list_user_bookings, name="list_user_bookings"),
    path("admin/all/", admin_list_all_bookings, name="admin_list_all_bookings"),
    path("admin/<int:booking_id>/detail/", admin_booking_detail, name="admin_booking_detail"),
]
