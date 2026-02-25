from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .models import Booking, BookingStatus
from apps.trains.models import Schedule
from apps.core.redis_client import redis_client
from .services import create_booking, cancel_booking, create_razorpay_order
from django.conf import settings


@login_required
def create_booking_ui(request, schedule_id):
    schedule = get_object_or_404(
        Schedule.objects.select_related(
            'train', 'source_station', 'destination_station'
        ),
        id=schedule_id
    )
    
    confirmed_seats = Booking.objects.filter(
        schedule_id=schedule_id,
        status=BookingStatus.CONFIRMED
    ).aggregate(total=Sum("passenger_count"))["total"] or 0
    
    locked_seats = redis_client.get(f"seat_lock:{schedule_id}")
    locked_seats = int(locked_seats) if locked_seats else 0
    
    available_seats = schedule.total_seats - confirmed_seats - locked_seats
    
    if request.method == 'POST':
        passengers = []
        i = 0
        while f'passenger_name_{i}' in request.POST:
            name = request.POST.get(f'passenger_name_{i}')
            age = request.POST.get(f'passenger_age_{i}')
            if name and age:
                passengers.append({
                    'name': name,
                    'age': int(age)
                })
            i += 1
        
        if not passengers:
            messages.error(request, 'Please add at least one passenger')
            return render(request, 'bookings/create.html', {
                'schedule': schedule,
                'available_seats': available_seats
            })
        
        booking, message = create_booking(request.user, schedule_id, passengers)
        
        if booking is None:
            messages.error(request, message)
            return render(request, 'bookings/create.html', {
                'schedule': schedule,
                'available_seats': available_seats
            })
        
        messages.success(request, f'Booking created successfully! Booking ID: #{booking.id}')
        return redirect('booking_detail_ui', booking_id=booking.id)
    
    return render(request, 'bookings/create.html', {
        'schedule': schedule,
        'available_seats': available_seats
    })


@login_required
def my_bookings_ui(request):
    bookings = Booking.objects.filter(
        user=request.user
    ).select_related(
        'schedule__train'
    ).order_by('-created_at')
    
    return render(request, 'bookings/list.html', {'bookings': bookings})


@login_required
def booking_detail_ui(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related(
            'schedule__train',
            'schedule__source_station',
            'schedule__destination_station'
        ).prefetch_related('passengers'),
        id=booking_id,
        user=request.user
    )
    
    return render(request, 'bookings/detail.html', {'booking': booking})


@login_required
def cancel_booking_ui(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        
        result_booking, message = cancel_booking(booking_id)
        
        if result_booking is None:
            messages.error(request, message)
        else:
            messages.success(request, message)
        
        return redirect('booking_detail_ui', booking_id=booking_id)
    
    return redirect('my_bookings_ui')


@login_required
def payment_ui(request, booking_id):
    from .services import LOCK_TTL
    from django.utils import timezone
    
    booking = get_object_or_404(
        Booking.objects.select_related('schedule__train'),
        id=booking_id,
        user=request.user
    )
    
    if booking.status != BookingStatus.PENDING:
        messages.warning(request, 'This booking is not eligible for payment')
        return redirect('booking_detail_ui', booking_id=booking_id)
    
    expiry_time = booking.created_at.timestamp() + LOCK_TTL
    current_time = timezone.now().timestamp()
    remaining_seconds = max(0, int(expiry_time - current_time))

    order = create_razorpay_order(booking)
    amount_rupees = order["amount"] / 100
    
    return render(request, 'bookings/payment.html', {
        'booking': booking,
        'expiry_timestamp': int(expiry_time * 1000),
        'remaining_seconds': remaining_seconds,
        'order_id': order["id"],
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'amount_rupees': amount_rupees,
    })
