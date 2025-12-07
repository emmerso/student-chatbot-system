from django.urls import path
from . import views

urlpatterns = [
    path('', views.chatbot, name='chatbot'),
    path('rasa-proxy/', views.rasa_proxy, name='rasa_proxy'),
    path('multilingual-chat/', views.multilingual_chat, name='multilingual_chat'),
    path('submit-feedback/', views.submit_feedback, name='submit_feedback'),
    path('notifications/', views.fetch_notifications, name='notifications'),

]
