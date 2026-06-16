from django.urls import path
from .views import AccessLogListView, TurnstileClientSearchView, TurnstileControlView

app_name = 'access'

urlpatterns = [
    path('', AccessLogListView.as_view(), name='access_log_list'),
    path('torniquete/', TurnstileControlView.as_view(), name='turnstile_control'),
    path('torniquete/buscar/', TurnstileClientSearchView.as_view(), name='turnstile_client_search'),
]
