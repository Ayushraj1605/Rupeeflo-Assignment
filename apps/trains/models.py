from django.db import models

# Create your models here.

class Station(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    city = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.code})"
    

class Train(models.Model):
    train_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.train_number} - {self.name}"


class Schedule(models.Model):
    train = models.ForeignKey(Train, on_delete=models.CASCADE)
    source_station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="departures"
    )
    destination_station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="arrivals"
    )

    travel_date = models.DateField()
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()

    total_seats = models.IntegerField()
    booking_cutoff_time = models.DateTimeField()

    def __str__(self):
        return f"{self.train} on {self.travel_date}"
