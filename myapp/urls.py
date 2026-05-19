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
    path('', views.home, name='home'),
]
