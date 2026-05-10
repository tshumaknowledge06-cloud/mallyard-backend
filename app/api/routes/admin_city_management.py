from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.city_request import CityRequest
from app.db.models.city import City
from app.db.models.user import User
from app.api.deps import get_current_user  
from pydantic import BaseModel

class CityApproval(BaseModel):
    country: str
    latitude: float
    longitude: float

router = APIRouter(prefix="/admin/cities", tags=["Admin Cities"])


@router.get("/requests")
def get_city_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return db.query(CityRequest).order_by(
        CityRequest.request_count.desc()
    ).all()


@router.post("/approve/{request_id}")
def approve_city(
    request_id: int,
    payload: CityApproval,  
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    req = db.query(CityRequest).filter(CityRequest.id == request_id).first()

    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Create real city using payload values
    city = City(
        name=req.name,
        country=payload.country,
        latitude=payload.latitude,
        longitude=payload.longitude,
        is_active=True
    )

    db.add(city)
    db.delete(req)
    db.commit()
    db.refresh(city)

    return city

@router.get("/cities")
def get_approved_cities(
    db: Session = Depends(get_db)
):
    """
    Public endpoint to get all approved cities
    """
    cities = db.query(City).filter(
        City.is_active == True
    ).order_by(City.name).all()
    
    # Convert to list of dicts without needing a schema
    return [
        {
            "id": city.id,
            "name": city.name,
            "country": city.country,
            "latitude": city.latitude,
            "longitude": city.longitude,
            "is_active": city.is_active,
        }
        for city in cities
    ]

