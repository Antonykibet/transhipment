from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import osmnx as ox
import networkx as nx
import osmnx.utils as ox_utils
import matplotlib
import os
from django.conf import settings
from django.shortcuts import render, get_object_or_404
import json
from django.views.decorators.csrf import csrf_exempt
from .models import Driver, Vehicle, Route, CurrentLocation
#from transhipment.planner.models import Current_location
import logging
Logger = logging.getLogger(__name__)

def index(request):
    template_name = 'hero.html'
    return render(request, template_name)

def login_page(request):
    template_name = 'login.html'
    return render(request, template_name)

def dashboard_page(request):
     # Fetch all drivers from the database
    drivers = Driver.objects.all()
    # Fetch all vehicles from the database
    vehicles = Vehicle.objects.all()
    latest_route = Route.objects.latest('id') 
    context = {
        'drivers': drivers,
        'vehicles': vehicles,
        'latest_route': latest_route,
    }
    template_name = 'dashboard.html'
    return render(request, template_name, context)

def get_location(request,vehicleID):
    vehicle = get_object_or_404(Vehicle, pk=vehicleID)
    latest_location = CurrentLocation.objects.filter(vehicle=vehicle).latest('timestamp')
    return JsonResponse({
            'lattitude': latest_location.latitude,
            'longitude': latest_location.longitude
        })

def tracker(request,vehicle_id):
    try:
        vehicle = get_object_or_404(Vehicle, pk=vehicle_id)

        latest_location = None
        try:
            latest_location = CurrentLocation.objects.filter(vehicle=vehicle).latest('timestamp')
        except CurrentLocation.DoesNotExist:
            pass # No location data for this vehicle yet

        context = {
            'vehicle': vehicle,
            'latest_location': latest_location,
            # Add any other data you need for the tracker page
        }
        return render(request, 'tracker.html', context) # You'll need a tracker_page.html template

    except Exception as e:
        print(f"Error in tracker view: {e}")
        # Consider a more user-friendly error response for production
        return HttpResponse(f"An error occurred: {e}", status=500)

@csrf_exempt
def update_location(request,vehicle_id):
    try:
        # First, verify the vehicle exists
        vehicle = get_object_or_404(Vehicle, pk=vehicle_id)

        # Process JSON data from request.body, not request.POST
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        print(f"Received data for vehicle_id {vehicle_id}: Lat={latitude}, Lon={longitude}")

        if latitude is None or longitude is None:
            return JsonResponse({'success': False, 'message': 'Latitude and Longitude are required.'}, status=400)

        # Convert to Decimal if your model fields are DecimalField
        # This is good practice for precision
        latitude = float(latitude) # Convert to float temporarily
        longitude = float(longitude) # Convert to float temporarily

        # Create (or update) the CurrentLocation record
        CurrentLocation.objects.create(
            vehicle=vehicle,
            latitude=latitude,
            longitude=longitude
        )
        return JsonResponse({'success': True, 'message': 'Location updated successfully.'})

    except Vehicle.DoesNotExist:
        print(f"Error: Vehicle with ID {vehicle_id} not found.")
        return JsonResponse({'success': False, 'message': 'Vehicle not found.'}, status=404)
    except json.JSONDecodeError:
        print("Error: Invalid JSON in request body.")
        return JsonResponse({'success': False, 'message': 'Invalid JSON in request body.'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        print(f"An unexpected error occurred: {e}")
        return JsonResponse({'success': False, 'message': f'Failed to update location: {e}'}, status=500)

def add_vehicle(request):
    number_plate = request.POST.get('number_plate')
    type = request.POST.get('type')
    brand = request.POST.get('brand')
    model = request.POST.get('model')
    consumption_per_km = int(request.POST.get('consumption'))
    created_vehicle = Vehicle.objects.create(number_plate=number_plate, type=type, brand=brand, model=model, consumption_per_km=consumption_per_km)
    return JsonResponse({'message': 'Created','creation':created_vehicle.brand})

def add_driver(request):
    name = request.POST.get('name')
    age = request.POST.get('age')
    created_driver = Driver.objects.create(name=name, age=age)
    return JsonResponse({'message': 'Created','creation':created_driver.name})

def router_planner(request):
    vehicle = request.POST.get('vehicle')
    driver = request.POST.get('driver')
    original_lat_str = request.POST.get('origin_lat')
    original_long_str = request.POST.get('origin_lon')
    destination_lat_str = request.POST.get('dest_lat')
    destination_lon_str = request.POST.get('dest_lon')
    origin_point = (float(original_lat_str), float(original_long_str))
    destination_point = (float(destination_lat_str), float(destination_lon_str))
    print(origin_point, destination_point)
        
    try:
        print('Starting...')
        G = generate_graph(origin_point)
        route = find_shortest_path(G, origin_point, destination_point)
        distance = calculate_distance(G,route)
        cost = calculate_fuel_consumption_cost(vehicle, distance)
        img_url = generate_route_image(G, route)
        payload = {
            "driver":driver,
            "vehicle":vehicle,
            "route_image":img_url,
            "destination_longitude":destination_lon_str,
            "destination_lattitude":destination_lat_str,
            "origin_longitude":original_long_str,
            "origin_lattitude":original_lat_str,
            "route_cost":cost,
            "distance":distance
        }
        save_generated_route(payload)
        print('Finished...')
        return JsonResponse({
            'success': True,
            'message': 'Route calculated and image generated.',
            'image_url': img_url,
        })
    except Exception as e:
        print(f'Failed generating the nodes and stuff: {e}',)
        return JsonResponse({
            'success': False,
            'message': 'Failed...',
            'image_path': '',
        })

    

def generate_graph(origin_point):
    try:
       G = ox.graph_from_point(origin_point, dist=10000, network_type='drive')
       return G
    except Exception as e:
        print(f'Failed to generate Graph:{e}')
        return ''

def find_shortest_path(G,origin_point, destination_point):
    try:
        orig_node = ox.nearest_nodes(G, origin_point[1], origin_point[0])
        dest_node = ox.nearest_nodes(G, destination_point[1], destination_point[0])
        route = nx.shortest_path(G, orig_node, dest_node,)
        return route
    except Exception as e:
        print(f'Failed to find shortest path...{e}')
        return ''

def generate_route_image(G, route):
    try:
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        image_dir = os.path.join(settings.MEDIA_ROOT, 'routes')
        os.makedirs(image_dir, exist_ok=True)
        import uuid
        image_filename = f'route_{uuid.uuid4()}.png'
        img_path_full = os.path.join(image_dir, image_filename)
        img_url = os.path.join(settings.MEDIA_URL, 'routes', image_filename)
        fig, ax = ox.plot_graph_route(
            G,
            route,
            route_color='r',
            route_linewidth=2,
            route_alpha=0.7,
            bgcolor='#FFFFFF',
            node_size=0,
            dpi=300,
            save=True,            # Re-add this argument
            filepath=img_path_full)
        plt.close(fig) 
        return img_url
    except Exception as e:
        print(f'Failed to generate image: {e}')

def calculate_fuel_consumption_cost(vehicle_id, distance):
    vehicle = Vehicle.objects.filter(id=vehicle_id).first()
    cost_per_km = vehicle.consumption_per_km
    total_cost = cost_per_km * distance
    return total_cost 

def calculate_distance(G,route):
    try:
        route_distance = ox.stats.edge_length_total(G)
        total_distance_km = route_distance / 1000.0 
        return total_distance_km
    except Exception as e:
        print("Failed to calculate distance: ",e)
        return 0

def save_generated_route(payload):
    driver_id = payload['driver']
    vehicle_id = payload['vehicle']
    driver = Driver.objects.filter(id=driver_id)[0]
    vehicle = Vehicle.objects.filter(id=vehicle_id)[0]
    payload['driver'] = driver
    payload['vehicle'] = vehicle
    return Route.objects.create(**payload)


@csrf_exempt
def user_register(request):
    print('hit')
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')

            if not username or not email or not password:
                return JsonResponse({'message': 'All fields are required.'}, status=400)

            if User.objects.filter(username=username).exists():
                return JsonResponse({'message': 'Username already exists.'}, status=400)
            if User.objects.filter(email=email).exists():
                return JsonResponse({'message': 'Email already registered.'}, status=400)

            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()

            print(f"User {username} registered successfully.")
            return JsonResponse({'message': 'Registration successful. Please log in.'}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            print("An error occurred during registration:")
            return JsonResponse({'message': f'An unexpected error occurred: {str(e)}'}, status=500)
    return JsonResponse({'message': 'Method not allowed'}, status=405)

@csrf_exempt 
def user_login(request):
    if request.method == 'POST':
        try:
            print('hit')
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                print(f"User {username} logged in successfully.")
                return JsonResponse({'message': 'Login successful'})
            else:
                print(f"Failed login attempt for username: {username}")
                return JsonResponse({'message': 'Invalid credentials'}, status=401)
        except json.JSONDecodeError:
            return JsonResponse({'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            print("An error occurred during login:")
            return JsonResponse({'message': f'An unexpected error occurred: {str(e)}'}, status=500)
    return JsonResponse({'message': 'Method not allowed'}, status=405)