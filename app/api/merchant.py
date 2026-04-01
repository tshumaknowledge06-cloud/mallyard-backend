from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.merchant import Merchant
from app.db.models.audit_log import AuditLog
from app.schemas.merchant import MerchantCreate, MerchantOut
from app.api.deps import get_current_user

router = APIRouter(
    prefix="/merchants",
    tags=["Merchants"]
)


# -------------------------
# Register merchant
# -------------------------
@router.post(
    "/register",
    response_model=MerchantOut,
    status_code=status.HTTP_201_CREATED
)
def register_merchant(
    merchant_in: MerchantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    existing = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Merchant profile already exists"
        )

    merchant = Merchant(
        user_id=current_user.id,
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


# -------------------------
# Approve merchant (ADMIN)
# -------------------------
@router.put("/{merchant_id}/approve", response_model=MerchantOut)
def approve_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    merchant = db.query(Merchant).filter(
        Merchant.id == merchant_id
    ).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    merchant.status = "approved"
    merchant.user.role = "seller"

    # 🔥 AUDIT LOG
    log = AuditLog(
        admin_id=current_user.id,
        merchant_id=merchant.id,
        action="approved"
    )

    db.add(log)
    db.commit()
    db.refresh(merchant)

    return merchant


# -------------------------
# Reject merchant (ADMIN)
# -------------------------
@router.put("/{merchant_id}/reject", response_model=MerchantOut)
def reject_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    merchant = db.query(Merchant).filter(
        Merchant.id == merchant_id
    ).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    merchant.status = "rejected"
    merchant.user.role = "buyer"  # downgrade if needed

    # 🔥 AUDIT LOG
    log = AuditLog(
        admin_id=current_user.id,
        merchant_id=merchant.id,
        action="rejected"
    )

    db.add(log)
    db.commit()
    db.refresh(merchant)

    return merchant


# -------------------------
# Pending merchants
# -------------------------
@router.get("/pending", response_model=list[MerchantOut])
def get_pending_merchants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    return db.query(Merchant).filter(
        Merchant.status == "pending_verification"
    ).all()
