from django.urls import path
from .views_ui import search_trains_ui

urlpatterns = [
    path('search/', search_trains_ui, name='search_trains_ui'),
]
