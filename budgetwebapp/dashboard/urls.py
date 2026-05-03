from django.urls import path
from . import views

urlpatterns = [
    path('home', views.index, name='home'),
    path('<slug:slug>/', views.dashboard_view, name='dashboard'),
    path('api/widgets/update-layout/', views.update_widget_layout, name='update_widget_layout'),
]