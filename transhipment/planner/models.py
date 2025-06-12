from django.db import models

# Create your models here.
class Vehicle(models.Model):
    number_plate = models.CharField(null=False,blank=False)
    brand = models.CharField(null=False,blank=False)
    model = models.CharField(null=False,blank=False)
    type = models.CharField(null=False,blank=False)
    consumption_per_km = models.IntegerField(default=1)

class Driver(models.Model):
    name = models.CharField(null=False,blank=False)
    age = models.IntegerField()


class Route(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    route_image = models.ImageField()
    destination_longitude = models.CharField(null=False,blank=False)
    destination_lattitude =  models.CharField(null=False,blank=False)
    origin_longitude =  models.CharField(null=False,blank=False)
    origin_lattitude =  models.CharField(null=False,blank=False)
    route_cost = models.IntegerField()
    distance = models.IntegerField()

class CurrentLocation(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='current_locations')
    latitude = models.DecimalField(max_digits=10, decimal_places=7) # Use DecimalField for precision
    longitude = models.DecimalField(max_digits=10, decimal_places=7) # Use DecimalField for precision
    timestamp = models.DateTimeField(auto_now_add=True) # Automatically sets creation time

