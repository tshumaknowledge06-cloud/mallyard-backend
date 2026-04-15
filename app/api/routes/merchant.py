from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.merchant import Merchant
from app.schemas.merchant import MerchantCreate, MerchantOut
from app.api.deps import get_current_user, require_role
from app.db.models.listing import Listing
from app.db.models.audit_log import AuditLog
from fastapi import UploadFile, File
from app.utils.file_upload import upload_file

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
    user_id: int,  # ✅ NEW: passed from frontend
    db: Session = Depends(get_db)
):

    # ✅ Ensure user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # ✅ Prevent duplicate merchant profiles
    existing = (
        db.query(Merchant)
        .filter(Merchant.user_id == user_id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Merchant profile already exists for this user"
        )

    # ✅ Create merchant
    merchant = Merchant(
        user_id=user_id,
        business_name=merchant_in.business_name,
        description=merchant_in.description,
        merchant_type=merchant_in.merchant_type,
        location=merchant_in.location,
        contact_phone=merchant_in.contact_phone,
        status="pending_verification"
    )

    db.add(merchant)
    db.commit()
    db.refresh(merchant)

    return merchant


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
    merchant_in: MerchantCreate,  # reuse schema for now
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    merchant = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    # ✅ Update only allowed fields
    merchant.business_name = merchant_in.business_name
    merchant.description = merchant_in.description
    merchant.location = merchant_in.location
    merchant.contact_phone = merchant_in.contact_phone

    db.commit()
    db.refresh(merchant)

    return merchant


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

    return pending_merchants

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