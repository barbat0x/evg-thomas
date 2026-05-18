from django.urls import path

from myapp import views

urlpatterns = [
    path('play/<int:pk>/', views.play_game, name='play_game'),
    path(
        'game/<int:pk>/compose/',
        views.compose_game,
        name='compose_game',
    ),
    path('commencer/', views.begin_party, name='begin_party'),
    path('setup/', views.setup_dashboard, name='setup'),
    path('', views.home, name='home'),
    path(
        'participants/<int:pk>/edit/',
        views.edit_participant,
        name='edit_participant',
    ),
    path(
        'teams/<int:pk>/edit/',
        views.edit_team,
        name='edit_team',
    ),
    path(
        'teams/<int:pk>/members/',
        views.manage_team_members,
        name='manage_team_members',
    ),
]
