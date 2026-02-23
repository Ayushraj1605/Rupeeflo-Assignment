from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.trains.models import Train, Station, Schedule

# Default route templates per train_number
ROUTES = {
    "12301": {"source": "DEL", "destination": "MUM", "hour": 16, "duration_hours": 16, "total_seats": 100},
    "12951": {"source": "MUM", "destination": "DEL", "hour": 17, "duration_hours": 16, "total_seats": 100},
    "12430": {"source": "DEL", "destination": "BLR", "hour": 20, "duration_hours": 36, "total_seats": 150},
    "12841": {"source": "DEL", "destination": "CHN", "hour": 22, "duration_hours": 28, "total_seats": 120},
}


class Command(BaseCommand):
    help = "Seed schedules for a date range per train using predefined routes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=14,
            help="Number of days from today to generate schedules (inclusive of today)",
        )

    def handle(self, *args, **options):
        days = options["days"]
        now = timezone.now()
        created = 0
        skipped = 0

        trains = Train.objects.all()
        if not trains.exists():
            self.stdout.write(self.style.ERROR("No trains found. Seed trains first."))
            return

        for train in trains:
            route = ROUTES.get(train.train_number)
            if not route:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f"Skipping train {train.train_number}: no route template configured.")
                )
                continue

            try:
                source = Station.objects.get(code=route["source"])
                destination = Station.objects.get(code=route["destination"])
            except Station.DoesNotExist:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping train {train.train_number}: missing station {route['source']} or {route['destination']}."
                    )
                )
                continue

            for offset in range(days):
                travel_date = (now + timedelta(days=offset)).date()
                departure_time = now.replace(hour=route["hour"], minute=0, second=0, microsecond=0) + timedelta(days=offset)
                arrival_time = departure_time + timedelta(hours=route["duration_hours"])
                booking_cutoff = departure_time - timedelta(hours=2)

                schedule, was_created = Schedule.objects.get_or_create(
                    train=train,
                    source_station=source,
                    destination_station=destination,
                    travel_date=travel_date,
                    defaults={
                        "departure_time": departure_time,
                        "arrival_time": arrival_time,
                        "total_seats": route["total_seats"],
                        "booking_cutoff_time": booking_cutoff,
                    },
                )
                if was_created:
                    created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} schedules. Skipped {skipped} trains without routes."))
