from django.urls import path
from . import views

urlpatterns = [
    path('health', views.health),
    path('metrics', views.metrics),
    path('greet-c', views.greet_c),
    path('slow', views.slow),
    path('fail', views.fail),
]
