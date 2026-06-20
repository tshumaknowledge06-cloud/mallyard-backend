from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.db.models.route import Route
from app.db.models.route_request import RouteRequest
from app.db.models.route_pricing import RoutePricing
from app.db.models.city import City
from app.services.delivery_pricing import suggest_route_pricing  

# ✅ FIX 1: Added router definition with prefix
router = APIRouter(prefix="/admin", tags=["Admin Routes"])

# ✅ Valid package types
VALID_PACKAGE_TYPES = ["small", "medium", "large"]

@router.get("/route-requests")
def get_route_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # ✅ Admin check
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return db.query(RouteRequest).order_by(
        RouteRequest.request_count.desc()
    ).all()

@router.post("/cities")
def create_city(
    name: str,
    country: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    city = City(name=name, country=country)
    db.add(city)
    db.commit()
    db.refresh(city)
    return city

@router.get("/cities")
def get_cities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    cities = db.query(City).all()
    return cities

@router.post("/routes")
def create_route(
    origin_city_id: int,
    destination_city_id: int,
    eta_min: int,
    eta_max: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # ✅ Admin check
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # ✅ Validate city IDs exist
    origin = db.query(City).filter(City.id == origin_city_id).first()
    destination = db.query(City).filter(City.id == destination_city_id).first()

    if not origin or not destination:
        raise HTTPException(status_code=400, detail="Invalid city IDs")
    
    # ✅ Check for duplicate route
    existing = db.query(Route).filter_by(
        origin_city_id=origin_city_id,
        destination_city_id=destination_city_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Route already exists")

    route = Route(
        origin_city_id=origin_city_id,
        destination_city_id=destination_city_id,
        estimated_days_min=eta_min,
        estimated_days_max=eta_max,
        is_active=True
    )

    db.add(route)
    db.commit()
    db.refresh(route)

    # ✅ Delete pending route requests for this city pair
    db.query(RouteRequest).filter_by(
        origin_city_id=origin_city_id,
        destination_city_id=destination_city_id
    ).delete()
    db.commit()

    return {
        "message": f"Route created from {origin.name} to {destination.name}",
        "route_id": route.id,
        "origin_city": origin.name,
        "destination_city": destination.name,
        "estimated_days_min": route.estimated_days_min,
        "estimated_days_max": route.estimated_days_max,
        "is_active": route.is_active
    }


@router.post("/routes/{route_id}/pricing")
def add_route_pricing(
    route_id: int,
    package_type: str,
    base_price: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # ✅ Admin check
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # ✅ Validate package_type
    if package_type not in VALID_PACKAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid package type. Must be one of: {', '.join(VALID_PACKAGE_TYPES)}"
        )

    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    # ✅ Check for duplicate pricing
    existing = db.query(RoutePricing).filter_by(
        route_id=route_id,
        package_type=package_type
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Pricing already exists for this package type"
        )

    pricing = RoutePricing(
        route_id=route_id,
        package_type=package_type,
        base_price=base_price
    )

    db.add(pricing)
    db.commit()
    db.refresh(pricing)

    return pricing


@router.put("/routes/{route_id}/pricing")
def update_route_pricing(
    route_id: int,
    small: float | None = None,
    medium: float | None = None,
    large: float | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # ✅ Admin check
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # ✅ Check route exists
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    # ✅ Track which packages are being updated
    updates = []
    if small is not None:
        updates.append(("small", small))
    if medium is not None:
        updates.append(("medium", medium))
    if large is not None:
        updates.append(("large", large))
    
    if not updates:
        raise HTTPException(status_code=400, detail="No pricing values provided")
    
    # ✅ Update or create pricing for each package type
    for package_type, price in updates:
        existing = db.query(RoutePricing).filter_by(
            route_id=route_id,
            package_type=package_type
        ).first()
        
        if existing:
            # ✅ Update existing
            existing.base_price = price
        else:
            # ✅ Create new if doesn't exist
            new_pricing = RoutePricing(
                route_id=route_id,
                package_type=package_type,
                base_price=price
            )
            db.add(new_pricing)
    
    db.commit()
    
    # ✅ Return updated pricing
    updated_pricing = db.query(RoutePricing).filter(
        RoutePricing.route_id == route_id
    ).all()
    
    return {
        "message": "Pricing updated successfully",
        "pricing": [
            {
                "package_type": p.package_type,
                "base_price": p.base_price
            }
            for p in updated_pricing
        ]
    }


@router.patch("/routes/{route_id}/toggle")
def toggle_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # ✅ Admin check
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    route = db.query(Route).filter(Route.id == route_id).first()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    route.is_active = not route.is_active

    db.commit()
    db.refresh(route)

    return {"status": "updated", "is_active": route.is_active}


@router.get("/routes")
def get_routes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # ✅ Admin check
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return db.query(Route).all()


@router.get("/route-requests/top")
def get_top_route_requests(
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # ✅ Admin check
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return db.query(RouteRequest).order_by(
        RouteRequest.request_count.desc()
    ).limit(limit).all()

@router.get("/route-insights")
def get_route_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 🔐 Admin check (consistent with your system)
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    requests = db.query(RouteRequest).order_by(
        RouteRequest.request_count.desc()
    ).limit(10).all()

    insights = []

    for req in requests:
        origin = db.query(City).get(req.origin_city_id)
        destination = db.query(City).get(req.destination_city_id)

        if not origin or not destination:
            continue

        pricing_suggestion = suggest_route_pricing(db, origin, destination)
        
        if not pricing_suggestion:
            continue
        
        insights.append({
            "origin": origin.name,
            "destination": destination.name,
            "demand": req.request_count,
            "distance_km": pricing_suggestion["distance_km"],
            "suggested_prices": pricing_suggestion["suggested_prices"]
        })

    return insights