from django.urls import path
from . import views

urlpatterns = [
    path('health', views.health),
    path('metrics', views.metrics),
    path('greet', views.greet),
    path('slow', views.slow),
    path('fail', views.fail),
]
