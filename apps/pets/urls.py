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
    # Siluetas de rutas para acciones de emparejamiento (Issue #63)
    path('match/like/', views.match_like_candidate_view, name='match_like_candidate'),
    path('match/pass/', views.match_pass_candidate_view, name='match_pass_candidate'),
    path('match/report/', views.match_report_candidate_view, name='match_report_candidate'),
    # Siluetas de rutas para solicitudes e interesados (Issue #64)
    path(
        'match/requests/<int:request_id>/accept/',
        views.match_accept_request_view,
        name='match_accept_request',
    ),
    path(
        'match/requests/<int:request_id>/reject/',
        views.match_reject_request_view,
        name='match_reject_request',
    ),
    path(
        'match/requests/<int:request_id>/note/',
        views.send_initial_note_view,
        name='send_initial_note',
    ),
    # Siluetas de rutas para citas y encuentros seguros (Issue #65)
    path('match/meetups/schedule/', views.schedule_meetup_view, name='schedule_meetup'),
    path('match/meetups/<int:meetup_id>/cancel/', views.cancel_meetup_view, name='cancel_meetup'),
]
