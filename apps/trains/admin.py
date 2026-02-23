from django.contrib import admin
from .models import Station, Train, Schedule

admin.site.register(Station)
admin.site.register(Train)
admin.site.register(Schedule)
