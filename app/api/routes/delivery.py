from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.security import get_password_hash
from app.db.session import get_db
from app.db.models.delivery_partner import DeliveryPartner
from app.schemas.delivery_partner import (
    DeliveryPartnerCreate,
    DeliveryPartnerUpdate,
    DeliveryPartnerOut
)
from app.api.deps import get_current_user
from app.db.models.user import User
from app.utils.file_upload import upload_file

router = APIRouter(
    prefix="/delivery",
    tags=["Delivery"]
)


# -------------------------
# Register Delivery Partner
# -------------------------
@router.post("/register", status_code=201)
def register_delivery_partner(
    payload: DeliveryPartnerCreate,
    db: Session = Depends(get_db),
):
    existing_user = db.query(User).filter(
        User.email == payload.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        hashed_password=get_password_hash(payload.password),
        role="delivery_partner",
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    partner = DeliveryPartner(
        user_id=user.id,
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        vehicle_type=payload.vehicle_type,
        license_number=payload.license_number,
        operating_city=payload.operating_city,
        is_active=False
    )

    db.add(partner)
    db.commit()
    db.refresh(partner)

    return {
        "message": "Registration successful. Await admin approval.",
        "partner_id": partner.id
    }


# -------------------------
# Current Delivery Partner Profile
# -------------------------
@router.get("/me", response_model=DeliveryPartnerOut)
def get_my_delivery_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "delivery_partner":
        raise HTTPException(status_code=403, detail="Only delivery partners can access")

    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.user_id == current_user.id
    ).first()

    if not partner:
        raise HTTPException(status_code=404, detail="Profile not found")

    if not partner.is_active:
        raise HTTPException(status_code=403, detail="Not yet approved")

    return partner


# -------------------------
# Update My Delivery Profile
# -------------------------
@router.put("/me", response_model=DeliveryPartnerOut)
def update_my_delivery_profile(
    payload: DeliveryPartnerUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "delivery_partner":
        raise HTTPException(status_code=403, detail="Only delivery partners allowed")

    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.user_id == current_user.id
    ).first()

    if not partner:
        raise HTTPException(status_code=404, detail="Profile not found")

    # ✅ Update allowed fields only
    partner.full_name = payload.full_name
    partner.phone_number = payload.phone_number
    partner.vehicle_type = payload.vehicle_type
    partner.license_number = payload.license_number
    partner.operating_city = payload.operating_city

    db.commit()
    db.refresh(partner)

    return partner


# -------------------------
# Admin - Pending Partners
# -------------------------
@router.get("/pending", response_model=list[DeliveryPartnerOut])
def get_pending_delivery_partners(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    return db.query(DeliveryPartner).filter(
        DeliveryPartner.is_active == False
    ).order_by(DeliveryPartner.created_at.desc()).all()


# -------------------------
# Public Directory (ACTIVE ONLY)
# -------------------------
@router.get("/", response_model=list[DeliveryPartnerOut])
def get_delivery_partners(
    city: str | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(DeliveryPartner).filter(
        DeliveryPartner.is_active == True
    )

    if city:
        query = query.filter(
            func.lower(DeliveryPartner.operating_city) == city.lower()
        )

    return query.all()


# -------------------------
# Public Delivery Profile
# -------------------------
@router.get("/{partner_id}", response_model=DeliveryPartnerOut)
def get_delivery_partner(
    partner_id: int,
    db: Session = Depends(get_db)
):
    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.id == partner_id
    ).first()

    if not partner:
        raise HTTPException(status_code=404, detail="Not found")

    if not partner.is_active:
        raise HTTPException(status_code=403, detail="Not approved")

    return partner


# -------------------------
# Admin Activate Partner
# -------------------------
@router.put("/{partner_id}/activate")
def activate_partner(
    partner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.id == partner_id
    ).first()

    if not partner:
        raise HTTPException(status_code=404, detail="Not found")

    partner.is_active = True
    db.commit()

    return {"message": "Activated"}


@router.post("/upload-profile-image")
def upload_profile_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "delivery_partner":
        raise HTTPException(status_code=403, detail="Only delivery partners allowed")

    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.user_id == current_user.id
    ).first()

    if not partner:
        raise HTTPException(status_code=404, detail="Delivery partner not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files allowed")

    # 🔥 CLOUD UPLOAD
    file_url = upload_file(file)

    partner.profile_image_url = file_url

    db.commit()
    db.refresh(partner)

    return {
        "message": "Profile image uploaded",
        "url": partner.profile_image_url
    }


@router.post("/upload-vehicle-image")
def upload_vehicle_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "delivery_partner":
        raise HTTPException(status_code=403, detail="Only delivery partners allowed")

    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.user_id == current_user.id
    ).first()

    if not partner:
        raise HTTPException(status_code=404, detail="Delivery partner not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files allowed")

    # 🔥 CLOUD UPLOAD
    file_url = upload_file(file)

    partner.vehicle_image_url = file_url

    db.commit()
    db.refresh(partner)

    return {
        "message": "Vehicle image uploaded",
        "url": partner.vehicle_image_url
    }