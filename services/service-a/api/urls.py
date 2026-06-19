from django.urls import path
from . import views

urlpatterns = [
    path('health', views.health),
    path('greet-service-b', views.greet_service_b),
    path('greeting-rcvd', views.greeting_rcvd),
]
