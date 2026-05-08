from django.urls import path
from . import views

urlpatterns = [
    path('home', views.index, name='home'),
    path('<slug:slug>/', views.dashboard_view, name='dashboard'),
    path('api/widgets/update-layout/', views.update_widget_layout, name='update_widget_layout'),
    path('api/widgets/<uuid:widget_id>/sidebar/', views.dashboard_sidebar_content, name='widget_sidebar'),
]