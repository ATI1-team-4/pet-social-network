from django.urls import path

from apps.accounts import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
]
