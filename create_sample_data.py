from django.utils import timezone
from datetime import timedelta
from apps.trains.models import Station, Train, Schedule

# Create Stations
stations_data = [
    {"name": "New Delhi", "code": "DEL", "city": "Delhi"},
    {"name": "Mumbai Central", "code": "MUM", "city": "Mumbai"},
    {"name": "Bangalore City", "code": "BLR", "city": "Bangalore"},
    {"name": "Chennai Central", "code": "CHN", "city": "Chennai"},
    {"name": "Kolkata Howrah", "code": "KOL", "city": "Kolkata"},
]

print("Creating stations...")
for data in stations_data:
    station, created = Station.objects.get_or_create(
        code=data["code"],
        defaults={"name": data["name"], "city": data["city"]}
    )
    print(f"  {'Created' if created else 'Exists'}: {station}")

# Create Trains
trains_data = [
    {"train_number": "12301", "name": "Rajdhani Express"},
    {"train_number": "12951", "name": "Mumbai Rajdhani"},
    {"train_number": "12430", "name": "Bangalore Express"},
    {"train_number": "12841", "name": "Chennai Mail"},
]

print("\nCreating trains...")
for data in trains_data:
    train, created = Train.objects.get_or_create(
        train_number=data["train_number"],
        defaults={"name": data["name"]}
    )
    print(f"  {'Created' if created else 'Exists'}: {train}")

# Create Schedules
print("\nCreating schedules...")
now = timezone.now()

schedules_data = [
    {
        "train": "12301",
        "source": "DEL",
        "destination": "MUM",
        "days_offset": 1,
        "hour": 16,
        "duration_hours": 16,
        "total_seats": 100
    },
    {
        "train": "12951",
        "source": "MUM",
        "destination": "DEL",
        "days_offset": 1,
        "hour": 17,
        "duration_hours": 16,
        "total_seats": 100
    },
    {
        "train": "12430",
        "source": "DEL",
        "destination": "BLR",
        "days_offset": 2,
        "hour": 20,
        "duration_hours": 36,
        "total_seats": 150
    },
    {
        "train": "12841",
        "source": "DEL",
        "destination": "CHN",
        "days_offset": 2,
        "hour": 22,
        "duration_hours": 28,
        "total_seats": 120
    },
    {
        "train": "12301",
        "source": "BLR",
        "destination": "MUM",
        "days_offset": 3,
        "hour": 9,
        "duration_hours": 24,
        "total_seats": 80
    },
]

for data in schedules_data:
    train = Train.objects.get(train_number=data["train"])
    source = Station.objects.get(code=data["source"])
    destination = Station.objects.get(code=data["destination"])
    
    travel_date = (now + timedelta(days=data["days_offset"])).date()
    departure_time = now + timedelta(days=data["days_offset"], hours=data["hour"] - now.hour)
    arrival_time = departure_time + timedelta(hours=data["duration_hours"])
    booking_cutoff = departure_time - timedelta(hours=2)
    
    schedule, created = Schedule.objects.get_or_create(
        train=train,
        source_station=source,
        destination_station=destination,
        travel_date=travel_date,
        defaults={
            "departure_time": departure_time,
            "arrival_time": arrival_time,
            "total_seats": data["total_seats"],
            "booking_cutoff_time": booking_cutoff
        }
    )
    print(f"  {'Created' if created else 'Exists'}: {train.name} {source.code}->{destination.code} on {travel_date}")

print("\n✓ Sample data created successfully!")
print("\nYou can now:")
print("1. Visit http://localhost:8000/")
print("2. Register/Login")
print("3. Search trains and make bookings")
