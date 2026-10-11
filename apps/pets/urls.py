from django.urls import path

from apps.pets import views

app_name = 'pets'

urlpatterns = [
    path('', views.pet_management_view, name='pet_management'),
    path('save/', views.pet_save_view, name='pet_save'),
    path('<str:pet_id>/delete/', views.pet_delete_view, name='pet_delete'),
    path('select/', views.pet_select_view, name='pet_select'),
    path('select/active/', views.pet_set_active_view, name='pet_set_active'),
    path('match/feed/', views.match_feed_view, name='match_feed'),
    path('match/interested/', views.match_interested_view, name='match_interested'),
]
