from django.urls import path
from . import views

urlpatterns = [
    path('home', views.index, name='home'),
    path("add-cell/", views.add_cell, name="add_cell"),
    path("delete-cell/", views.delete_cell, name="delete_cell"),
    path("run-cell/", views.run_cell_view, name="run_cell"),
]