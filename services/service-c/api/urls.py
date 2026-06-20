from django.urls import path
from . import views

urlpatterns = [
    path('health', views.health),
    path('greet-c', views.greet_c),
]
