from django.urls import path

from apps.pets import views

app_name = 'pets'

urlpatterns = [
    path('', views.pet_management_view, name='pet_management'),
    path('select/', views.pet_select_view, name='pet_select'),
    path('match/feed/', views.match_feed_view, name='match_feed'),
    path('match/interested/', views.match_interested_view, name='match_interested'),
]
