from django.urls import path
from .views_ui import (
    create_booking_ui,
    my_bookings_ui,
    booking_detail_ui,
    cancel_booking_ui,
    payment_ui
)

urlpatterns = [
    path('create/<int:schedule_id>/', create_booking_ui, name='create_booking_ui'),
    path('my-bookings/', my_bookings_ui, name='my_bookings_ui'),
    path('detail/<int:booking_id>/', booking_detail_ui, name='booking_detail_ui'),
    path('cancel/<int:booking_id>/', cancel_booking_ui, name='cancel_booking_ui'),
    path('payment/<int:booking_id>/', payment_ui, name='payment_ui'),
]
