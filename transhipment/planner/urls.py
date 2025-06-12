from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_page, name="index"),
    path("dashboard", views.dashboard_page, name="dashboard_page"),
    path("plan", views.router_planner, name="router_planner"),
    path("add_driver", views.add_driver, name="add_driver"),
    path("add_vehicle", views.add_vehicle, name="add_vehicle"),
    path("tracker/<int:vehicle_id>/", views.tracker, name="track"),
    path("update_location/<int:vehicle_id>/", views.update_location, name="update_location"),
    path("get_location/<int:vehicleID>/", views.get_location, name="get_location"),
]