from django.urls import path
from .views import search_trains

urlpatterns = [
    path("search/", search_trains),
]
