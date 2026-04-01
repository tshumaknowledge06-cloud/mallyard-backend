from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.category import Category
from app.db.models.subcategory import SubCategory
from app.db.models.listing import Listing
from app.db.models.order import Order
from app.db.models.user import User
from app.db.models.merchant import Merchant
from app.api.deps import get_db, get_current_user_optional
from sqlalchemy import or_


router = APIRouter(
    prefix="/sandy",
    tags=["Sandy AI"]
)


from sqlalchemy.orm import joinedload
from sqlalchemy import or_

@router.get("/discovery")
def sandy_discovery(
    query: str,
    db: Session = Depends(get_db)
):
    search = f"%{query.lower()}%"

    listings = (
        db.query(Listing)
        .options(
            joinedload(Listing.merchant),
            joinedload(Listing.subcategory)
        )
        .join(Merchant, Listing.merchant_id == Merchant.id)
        .join(SubCategory, Listing.subcategory_id == SubCategory.id)
        .filter(
            or_(
                Listing.name.ilike(search),
                Listing.description.ilike(search),
                Merchant.business_name.ilike(search),
                SubCategory.name.ilike(search),          # ✅ subcategory search
            )
        )
        .limit(30)
        .all()
    )

    results = []

    for listing in listings:
        results.append({
            "id": listing.id,
            "name": listing.name,
            "description": listing.description,
            "price": listing.price,
            "currency": listing.currency,
            "listing_type": listing.listing_type,

            # ✅ MEDIA (CRITICAL)
            "image_urls": listing.image_urls or [],
            "video_url": listing.video_url,

            # ✅ FULL MERCHANT
            "merchant": {
                "id": listing.merchant.id if listing.merchant else None,
                "business_name": listing.merchant.business_name if listing.merchant else "Unknown"
            },

            # ✅ SUBCATEGORY
            "subcategory": {
                "id": listing.subcategory.id if listing.subcategory else None,
                "name": listing.subcategory.name if listing.subcategory else "",
                "category_id": listing.subcategory.category_id if listing.subcategory else None
            }
        })

    return results


@router.post("/chat")
def sandy_chat(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    message = payload.get("message", "").lower().strip()

    if not message:
        return {
            "intent": "unknown",
            "reply": "Please type a message so I can help you."
        }

    # -------------------------------------------------
    # KEYWORD LIBRARIES
    # -------------------------------------------------

    order_keywords = ["order", "delivery", "package"]
    tracking_keywords = ["where", "track", "status", "arrived", "coming", "check"]

    buyer_keywords = [
        "want", "buy", "find", "show", "looking",
        "need", "get", "search"
    ]

    seller_keywords = [
        "sell", "list", "merchant", "register",
        "start selling"
    ]

    help_keywords = ["how", "help", "guide"]

    stop_words = {
        "i", "me", "my", "a", "an", "the", "for", "to", "of", "on", "in",
        "find", "show", "want", "need", "get", "search", "looking", "listings",
        "listing", "please", "some", "any"
    }

    # -------------------------------------------------
    # SEMANTIC LANGUAGE MAP
    # -------------------------------------------------

    semantic_map = {
        "groceries": ["drink", "food", "bread", "milk", "sprite", "coke"],
        "drinks": ["sprite", "coke", "fanta", "juice", "water"],
        "electronics": ["phone", "iphone", "laptop", "tv"],
        "services": ["repair", "cleaning", "delivery", "booking"]
    }

    # -------------------------------------------------
    # INTENT 1 — ORDER TRACKING
    # Protected: requires login
    # -------------------------------------------------

    if any(word in message for word in order_keywords) and any(word in message for word in tracking_keywords):
        if not current_user:
            return {
                "intent": "auth_required",
                "reply": (
                    "Please log in to continue. Go to the login page and sign in, "
                    "then I can help you track your orders."
                )
            }

        order = (
            db.query(Order)
            .filter(Order.buyer_id == current_user.id)
            .order_by(Order.created_at.desc())
            .first()
        )

        if not order:
            return {
                "intent": "order_tracking",
                "reply": "You currently have no orders."
            }

        return {
            "intent": "order_tracking",
            "reply": f"Your latest order, number {order.id}, is currently: {order.status}"
        }

    # -------------------------------------------------
    # INTENT 2 — BUYER SEARCH ENGINE
    # Guest-safe
    # -------------------------------------------------

    if any(word in message for word in buyer_keywords):
        raw_terms = message.split()
        search_terms = [
            term.strip(".,!?")
            for term in raw_terms
            if term.strip(".,!?") and term.strip(".,!?") not in stop_words
        ]

        for concept, related_words in semantic_map.items():
            if concept in message:
                for word in related_words:
                    if word not in search_terms:
                        search_terms.append(word)

        matched_results = []
        seen_listing_ids = set()

        listings = (
            db.query(Listing)
            .join(Merchant, Listing.merchant_id == Merchant.id)
            .limit(50)
            .all()
        )

        for listing in listings:
            listing_name = (listing.name or "").lower()
            listing_description = (listing.description or "").lower()
            listing_text = f"{listing_name} {listing_description}"

            score = 0

            for term in search_terms:
                if term == listing_name:
                    score += 5
                elif term in listing_name:
                    score += 3
                elif term in listing_description:
                    score += 1

            if score > 0 and listing.id not in seen_listing_ids:
                merchant_name = (
                    listing.merchant.business_name
                    if listing.merchant
                    else "Unknown Seller"
                )

                matched_results.append({
                    "id": listing.id,
                    "text": f"{listing.name} — ${listing.price} — {merchant_name}",
                    "score": score
                })
                seen_listing_ids.add(listing.id)

        categories = db.query(Category).all()

        for category in categories:
            category_name = (category.name or "").lower()

            if category_name in message:
                category_listings = (
                    db.query(Listing)
                    .filter(Listing.category_id == category.id)
                    .limit(10)
                    .all()
                )

                for listing in category_listings:
                    if listing.id in seen_listing_ids:
                        continue

                    merchant_name = (
                        listing.merchant.business_name
                        if listing.merchant
                        else "Unknown Seller"
                    )

                    matched_results.append({
                        "id": listing.id,
                        "text": f"{listing.name} — ${listing.price} — {merchant_name}",
                        "score": 2
                    })
                    seen_listing_ids.add(listing.id)

        subcategories = db.query(SubCategory).all()

        for subcategory in subcategories:
            subcategory_name = (subcategory.name or "").lower()

            if subcategory_name in message:
                sub_listings = (
                    db.query(Listing)
                    .filter(Listing.subcategory_id == subcategory.id)
                    .limit(10)
                    .all()
                )

                for listing in sub_listings:
                    if listing.id in seen_listing_ids:
                        continue

                    merchant_name = (
                        listing.merchant.business_name
                        if listing.merchant
                        else "Unknown Seller"
                    )

                    matched_results.append({
                        "id": listing.id,
                        "text": f"{listing.name} — ${listing.price} — {merchant_name}",
                        "score": 2
                    })
                    seen_listing_ids.add(listing.id)

        if matched_results:
            matched_results = sorted(
                matched_results,
                key=lambda item: item["score"],
                reverse=True
            )

            results_text = "\n".join(
                item["text"] for item in matched_results[:10]
            )

            return {
                "intent": "buyer_discovery",
                "reply": f"I found these products or services:\n\n{results_text}"
            }

        return {
            "intent": "buyer_discovery",
            "reply": "I couldn't find that product or service yet. Try searching with a more specific product or service name."
        }

    # -------------------------------------------------
    # INTENT 3 — SELLER HELP
    # Guest-safe
    # -------------------------------------------------

    if any(word in message for word in seller_keywords) or any(word in message for word in help_keywords):
        return {
            "intent": "seller_help",
            "reply": (
                "To start selling products or services on The Mallyard:\n\n"
                "1️⃣ Register as a Merchant\n"
                "2️⃣ Create your store profile\n"
                "3️⃣ Add product or service listings\n"
                "4️⃣ Start receiving orders or bookings\n\n"
                "You can register as a merchant from the merchant signup page."
            )
        }

    # -------------------------------------------------
    # INTENT 4 — ABOUT THE MALLYARD
    # Guest-safe
    # -------------------------------------------------

    if "mallyard" in message:
        return {
            "intent": "about_mallyard",
            "reply": (
                "The Mallyard is a digital marketplace where customers can discover and purchase products or book services "
                "from trusted local or global merchants and service providers. "
                "It connects buyers with businesses, making it easy to explore groceries, electronics, services, and more "
                "all in one platform. Sellers can create stores, list their products or services, and receive orders or bookings "
                "from customers through the platform."
            )
        }

    # -------------------------------------------------
    # FALLBACK
    # -------------------------------------------------

    return {
        "intent": "unknown",
        "reply": (
            "I'm still learning. You can ask me to find products or services, "
            "track orders, or help you start selling."
        )
    }