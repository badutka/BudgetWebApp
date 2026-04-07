from django.urls import path
from . import views

urlpatterns = [
    path('home', views.home_view, name='home'),
    path('portfolio', views.portfolio_view, name='portfolio'),
    path('portfolio/account-details/<str:account_type>/', views.account_details, name='account_details'),
    # path('dashboard/', views.dashboard_view, name='dashboard'),  # unified view
    path('dashboard/<slug:slug>/', views.dashboard_view, name='dashboard')
]