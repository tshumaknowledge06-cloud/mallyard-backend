from app.db.models.route import Route
from app.db.models.route_pricing import RoutePricing
from app.db.models.route_request import RouteRequest


def get_intercity_price(db, origin_city_id, destination_city_id, package_type):
    route = db.query(Route).filter_by(
        origin_city_id=origin_city_id,
        destination_city_id=destination_city_id,
        is_active=True
    ).first()

    if not route:
        return None

    pricing = db.query(RoutePricing).filter_by(
        route_id=route.id,
        package_type=package_type
    ).first()

    if not pricing:
        return None

    return pricing.base_price, route.estimated_days_min, route.estimated_days_max


def handle_missing_route(db, origin_city_id, destination_city_id):
    existing = db.query(RouteRequest).filter_by(
        origin_city_id=origin_city_id,
        destination_city_id=destination_city_id
    ).first()

    if existing:
        existing.request_count += 1
    else:
        new_request = RouteRequest(
            origin_city_id=origin_city_id,
            destination_city_id=destination_city_id,
            request_count=1
        )
        db.add(new_request)

import math

def calculate_distance_km(lat1, lon1, lat2, lon2):
    R = 6371

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def get_intracity_price(merchant, customer):
    
    # ❌ Missing coordinates → fallback
    if not all([
        merchant.latitude is not None,
        merchant.longitude is not None,
        customer.latitude is not None,
        customer.longitude is not None
    ]):
        return None

    distance = calculate_distance_km(
        merchant.latitude,
        merchant.longitude,
        customer.latitude,
        customer.longitude
    ) * 1.3  # realism multiplier

    base_fee = 1.5
    per_km = 0.5

    price = base_fee + (distance * per_km)

    # minimum charge
    price = max(price, 2.5)

    return round(price, 2)


def calculate_delivery(db, merchant, customer, package_type="medium"):
    
    response = {
        "type": None,
        "price": None,
        "eta": None,
        "available": True,
        "message": None
    }

    # ❌ Missing city info
    if not merchant.city_id or not customer.city_id:
        response["available"] = False
        response["message"] = "Delivery location incomplete"
        return response

    # 🟢 INTRA-CITY
    if merchant.city_id == customer.city_id:

        price = get_intracity_price(merchant, customer)

        response["type"] = "intra_city"
        response["eta"] = "Same day"

        if price:
            response["price"] = price
        else:
            response["message"] = "Delivery price will be confirmed"

        return response

    # 🔵 INTER-CITY
    result = get_intercity_price(
        db,
        merchant.city_id,
        customer.city_id,
        package_type
    )

    response["type"] = "inter_city"

    if result:
        price, eta_min, eta_max = result

        response["price"] = price
        response["eta"] = f"{eta_min}-{eta_max} days"

    else:
        handle_missing_route(
            db,
            merchant.city_id,
            customer.city_id
        )

        response["available"] = False
        response["message"] = "Route not available yet"

    return response

def suggest_route_price(distance_km, package_type):
    base_fees = {
        "small": 2,
        "medium": 3,
        "large": 5
    }

    per_km_rates = {
        "small": 0.4,
        "medium": 0.6,
        "large": 0.9
    }

    base = base_fees.get(package_type, 3)
    per_km = per_km_rates.get(package_type, 0.6)

    price = base + (distance_km * per_km)

    return round(price, 2)

def suggest_route_pricing(db, origin_city, destination_city):
    # ✅ SAFETY CHECK: Ensure all coordinates exist before calculating
    if not all([
        origin_city.latitude,
        origin_city.longitude,
        destination_city.latitude,
        destination_city.longitude
    ]):
        return None

    distance = calculate_distance_km(
        origin_city.latitude,
        origin_city.longitude,
        destination_city.latitude,
        destination_city.longitude
    )

    suggestions = {}

    for pkg in ["small", "medium", "large"]:
        suggestions[pkg] = suggest_route_price(distance, pkg)

    return {
        "distance_km": round(distance, 2),
        "suggested_prices": suggestions
    }