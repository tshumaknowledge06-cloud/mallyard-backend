from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.city_request import CityRequest
from app.db.models.city import City
from app.db.models.user import User
from app.api.deps import get_current_user  

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
    country: str,
    latitude: float,
    longitude: float,
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

    # Create real city
    city = City(
        name=req.name,
        country=country,
        latitude=latitude,
        longitude=longitude,
        is_active=True
    )

    db.add(city)

    # Remove request
    db.delete(req)

    db.commit()
    db.refresh(city)

    return city