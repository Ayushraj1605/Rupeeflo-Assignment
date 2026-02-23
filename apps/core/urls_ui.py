from django.urls import path
from .views_ui import register_ui, login_ui, logout_ui

urlpatterns = [
    path('register/', register_ui, name='register_ui'),
    path('login/', login_ui, name='login_ui'),
    path('logout/', logout_ui, name='logout_ui'),
]
