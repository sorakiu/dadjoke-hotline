from django.urls import path
from . import views

urlpatterns = [
    path('answer', views.answer, name='api-answer'),
    path('event', views.event, name='api-event'),
    path('fallback', views.fallback, name='api-fallback'),
    path('inbound', views.inbound, name='api-inbound'),
    path('healthz', views.healthz, name='api-healthz'),
]
