from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password


def register_ui(request):
    if request.user.is_authenticated:
        return redirect('search_trains_ui')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        if password != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'auth/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'auth/register.html')
        
        User.objects.create(
            username=username,
            password=make_password(password)
        )
        messages.success(request, 'Account created successfully! Please login.')
        return redirect('login_ui')
    
    return render(request, 'auth/register.html')


def login_ui(request):
    if request.user.is_authenticated:
        return redirect('search_trains_ui')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {username}!')
            return redirect('search_trains_ui')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'auth/login.html')


def logout_ui(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('login_ui')
