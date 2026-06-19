from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import random 

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.merchant import Merchant
from app.schemas.merchant import MerchantCreate, MerchantOut, MerchantUpdate
from app.api.deps import get_current_user, require_role
from app.db.models.listing import Listing
from app.db.models.audit_log import AuditLog
from fastapi import UploadFile, File
from app.utils.file_upload import upload_file
from app.services.city_service import resolve_city
from app.db.models.city_request import CityRequest

router = APIRouter(
    prefix="/merchants",
    tags=["Merchants"]
)

# -------------------------
# Health check
# -------------------------
@router.get("/health")
def merchant_health_check():
    return {"status": "merchant routes alive"}


# -------------------------
# Register merchant profile
# -------------------------
@router.post(
    "/register",
    response_model=MerchantOut,
    status_code=status.HTTP_201_CREATED
)
def register_merchant(
    merchant_in: MerchantCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(Merchant).filter(Merchant.user_id == user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Merchant already exists")

    # 🔥 NORMALIZE INPUT
    city_name = merchant_in.city_name.strip().lower() if merchant_in.city_name else None

    # 🔥 RESOLVE CITY 
    city_id = None

    if city_name:
        city_id = resolve_city(db, city_name)

        if not city_id:
            # 🔥 UPSERT CITY REQUEST (normalized)
            existing_request = db.query(CityRequest).filter(
                CityRequest.name == city_name
            ).first()

            if existing_request:
                existing_request.request_count += 1
            else:
                new_request = CityRequest(name=city_name)
                db.add(new_request)

    merchant = Merchant(
        user_id=user_id,
        business_name=merchant_in.business_name,
        description=merchant_in.description,
        merchant_type=merchant_in.merchant_type,
        location=merchant_in.location,
        contact_phone=merchant_in.contact_phone,
        pickup_address=merchant_in.pickup_address,
        city_id=city_id,
        status="pending_verification"
    )

    db.add(merchant)
    db.commit()
    db.refresh(merchant)

    return {
         "id": merchant.id,
         "business_name": merchant.business_name,
         "description": merchant.description,
         "merchant_type": merchant.merchant_type,
         "location": merchant.location,
         "contact_phone": merchant.contact_phone,
         "pickup_address": merchant.pickup_address,
         "city_id": merchant.city_id if merchant.city_id else 0,
         "city_name": merchant.city.name if merchant.city else None,  
         "status": merchant.status,
         "user_id": merchant.user_id,
         "created_at": merchant.created_at,  
}


@router.get("/me")
def get_my_merchant(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    merchant = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant profile not found")

    return {
        "merchant": {
            "id": merchant.id,
            "business_name": merchant.business_name,
            "logo_url": merchant.logo_url,
            "description": merchant.description,
            "merchant_type": merchant.merchant_type,
            "location": merchant.location,
            "contact_phone": merchant.contact_phone,
            "status": merchant.status
        }
    }


# -------------------------
# Update My Merchant Profile
# -------------------------
@router.put("/me", response_model=MerchantOut)
def update_my_merchant(
    merchant_in: MerchantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    merchant = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    # 🔥 NORMALIZE INPUT
    city_name = merchant_in.city_name.strip().lower() if merchant_in.city_name else None

    # 🔥 RESOLVE CITY 
    city_id = None

    if city_name:
        city_id = resolve_city(db, city_name)

        if not city_id:
            # 🔥 UPSERT CITY REQUEST (normalized)
            existing_request = db.query(CityRequest).filter(
                CityRequest.name == city_name
            ).first()

            if existing_request:
                existing_request.request_count += 1
            else:
                new_request = CityRequest(name=city_name)
                db.add(new_request)

        merchant.city_id = city_id

    # 🔥 SAFE FIELD UPDATES (only if provided)
    if merchant_in.business_name is not None:
        merchant.business_name = merchant_in.business_name

    if merchant_in.description is not None:
        merchant.description = merchant_in.description

    if merchant_in.location is not None:
        merchant.location = merchant_in.location

    if merchant_in.pickup_address is not None:
        merchant.pickup_address = merchant_in.pickup_address

    if merchant_in.contact_phone is not None:
        merchant.contact_phone = merchant_in.contact_phone

    db.commit()
    db.refresh(merchant)

    return {
        "id": merchant.id,
        "business_name": merchant.business_name,
        "description": merchant.description,
        "merchant_type": merchant.merchant_type, 
        "location": merchant.location,
        "contact_phone": merchant.contact_phone,
        "pickup_address": merchant.pickup_address,
        "city_id": merchant.city_id if merchant.city_id else 0, 
        "city_name": merchant.city.name if merchant.city else None,
        "status": merchant.status,  
        "created_at": merchant.created_at,
        "user_id": merchant.user_id,
    }


# -------------------------
# Approve merchant (ADMIN ONLY)
# -------------------------
@router.put(
    "/{merchant_id}/approve",
    response_model=MerchantOut
)
def approve_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can approve merchants"
        )

    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()

    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not found"
        )

    # 🔥 Log action
    log = AuditLog(
        action="approve_merchant",
        performed_by=current_user.id,
        target_id=merchant.id
    )
    db.add(log)

    merchant.status = "approved"
    merchant.user.role = "seller"

    db.commit()
    db.refresh(merchant)

    return merchant

# -------------------------
# Get All Pending Merchants (Admin Only)
# -------------------------
@router.get(
    "/pending",
    response_model=list[MerchantOut]
)
def get_pending_merchants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view pending merchants"
        )

    pending_merchants = (
        db.query(Merchant)
        .filter(Merchant.status == "pending_verification")
        .all()
    )

    response = []
    for m in pending_merchants:  # ✅ Fixed: iterate over pending_merchants, use 'm' as variable
        response.append({
            "id": m.id,  # ✅ Fixed: use 'm.id'
            "business_name": m.business_name,  # ✅ Fixed: use 'm.business_name'
            "description": m.description,  # ✅ Fixed: use 'm.description'
            "merchant_type": m.merchant_type,  # ✅ Fixed: use 'm.merchant_type'
            "location": m.location,  # ✅ Fixed: use 'm.location'
            "contact_phone": m.contact_phone,  # ✅ Fixed: use 'm.contact_phone'
            "pickup_address": m.pickup_address,  # ✅ Fixed: use 'm.pickup_address'
            "city_id": m.city_id if m.city_id else 0,  # ✅ Fixed: use 'm.city_id'
            "city_name": m.city.name if m.city else None,  # ✅ Fixed: use 'm.city'
            "status": m.status,  # ✅ Fixed: use 'm.status'
            "user_id": m.user_id,  # ✅ Fixed: use 'm.user_id'
            "logo_url": m.logo_url,  # ✅ Fixed: use 'm.logo_url'
            "created_at": m.created_at,  # ✅ Fixed: use 'm.created_at'
        })

    return response

# -------------------------
# Public Merchant Storefront
# -------------------------
@router.get("/{merchant_id}/storefront")
def get_merchant_storefront(
    merchant_id: int,
    db: Session = Depends(get_db)
):
    # Get merchant
    merchant = (
        db.query(Merchant)
        .filter(Merchant.id == merchant_id)
        .first()
    )

    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not found"
        )

    # Only approved merchants can have public storefront
    if merchant.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Merchant not approved"
        )

    # Get active listings for this merchant
    listings = (
        db.query(Listing)
        .filter(
            Listing.merchant_id == merchant_id,
            Listing.is_active == True
        )
        .all()
    )

    return {
        "merchant": {
            "id": merchant.id,
            "business_name": merchant.business_name,
            "logo_url": merchant.logo_url,
            "description": merchant.description,
            "merchant_type": merchant.merchant_type,
            "location": merchant.location,
            "contact_phone": merchant.contact_phone,
            "status": merchant.status,
        },
        "listings": listings
    }

# -------------------------
# Reject merchant (ADMIN ONLY)
# -------------------------
@router.put(
    "/{merchant_id}/reject",
    response_model=MerchantOut
)
def reject_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can reject merchants"
        )

    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()

    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not found"
        )

    # Log audit action
    log = AuditLog(
        action="reject_merchant",
        performed_by=current_user.id,
        target_id=merchant.id
    )
    db.add(log)

    # Only change merchant status
    merchant.status = "rejected"

    db.commit()
    db.refresh(merchant)

    return merchant

@router.put("/me/payment-methods")
def update_payment_methods(
    methods: list[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("seller"))
):
    merchant = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    merchant.payment_methods = methods
    db.commit()
    db.refresh(merchant)

    return merchant


@router.post("/upload-logo")
def upload_merchant_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "seller":
        raise HTTPException(status_code=403, detail="Only merchants allowed")

    merchant = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files allowed")

    # 🔥 CLOUD UPLOAD
    file_url = upload_file(file)

    merchant.logo_url = file_url

    db.commit()
    db.refresh(merchant)

    return {
        "message": "Logo uploaded successfully",
        "logo_url": merchant.logo_url
    }

@router.get("/approved")
def get_approved_merchants(
    db: Session = Depends(get_db)
):
    """
    Public endpoint to get all approved merchants for the featured merchants section
    """
    merchants = db.query(Merchant).filter(
        Merchant.status == "approved"
    ).all()
    
    result = [
        {
            "id": merchant.id,
            "business_name": merchant.business_name,
            "logo_url": merchant.logo_url
        }
        for merchant in merchants
    ]
    
    random.shuffle(result)
    
    return result