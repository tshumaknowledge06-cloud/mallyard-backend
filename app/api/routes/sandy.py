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
        .outerjoin(SubCategory, Listing.subcategory_id == SubCategory.id)
        .filter(Merchant.status == "approved")
        .filter(
            or_(
                Listing.name.ilike(search),
                Listing.description.ilike(search),
                Merchant.business_name.ilike(search),
                SubCategory.name.ilike(search),          
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

    # 🔥 NEW: Split help keywords
    general_help_keywords = ["help", "guide", "assist", "support"]
    seller_help_keywords = ["how to sell", "become a seller", "start selling", "seller registration"]

    # 🔥 NEW: Greeting keywords
    greeting_keywords = [
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
        "morning", "afternoon", "evening", "howdy", "greetings"
    ]

    # 🔥 NEW: Identity keywords
    identity_keywords = [
        "who are you", "what are you", "who is sandy", "what is sandy",
        "tell me about yourself", "what can you do", "your name"
    ]

    # 🔥 NEW: Thanks keywords
    thanks_keywords = [
        "thanks", "thank you", "appreciate it", "thanks sandy", "thank u",
        "thx", "appreciate you"
    ]

    # 🔥 NEW: Goodbye keywords
    goodbye_keywords = [
        "bye", "goodbye", "see you", "see ya", "farewell", "talk later",
        "bye bye", "catch you later"
    ]

    # 🔥 NEW: Delivery help keywords
    delivery_keywords = [
        "delivery", "shipping", "courier", "transport", "deliver",
        "delivery fee", "delivery fees", "delivery time", "delivery cost"
    ]

    # 🔥 NEW: Payment help keywords
    payment_keywords = [
        "payment", "pay", "ecocash", "onemoney", "innbucks", "cash on delivery",
        "cod", "mobile money", "card", "currency", "bank transfer", "zipit",
        "how to pay", "payment method"
    ]

    # 🔥 NEW: Merchant Growth keywords
    merchant_growth_keywords = [
        "good listing", "listing tips", "create a good listing",
        "attract customers", "get customers", "more customers",
        "increase sales", "sell more", "boost sales",
        "no orders", "not getting orders", "no sales",
        "how many photos", "listing photos", "product photos",
        "trust seller", "customer trust", "build trust",
        "selling tip", "daily tip", "merchant tip"
    ]

    stop_words = {
        "i", "me", "my", "a", "an", "the", "for", "to", "of", "on", "in",
        "find", "show", "want", "need", "get", "search", "looking", "listings",
        "listing", "please", "some", "any", "am"
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
    # INTENT 0 — GREETING (NEW)
    # -------------------------------------------------
    if any(word in message for word in greeting_keywords):
        return {
            "intent": "greeting",
            "reply": (
                "👋 **Welcome to The Mallyard.**\n\n"
                "I'm Sandy, your marketplace assistant.\n\n"
                "**I can help you:**\n"
                "• Find products and services\n"
                "• Track your orders\n"
                "• Start selling on The Mallyard\n"
                "• Answer questions about deliveries and payments\n\n"
                "**How can I help you today?**"
            )
        }

    # -------------------------------------------------
    # INTENT 0.1 — IDENTITY (NEW)
    # -------------------------------------------------
    if any(phrase in message for phrase in identity_keywords):
        return {
            "intent": "identity",
            "reply": (
                "✨ **I'm Sandy** — your digital concierge and trusted guide to The Mallyard.\n\n"
                "I'm here to help you discover products, track orders, understand deliveries, "
                "learn about payments, and grow your business on the platform.\n\n"
                "**What would you like to explore today?**"
            )
        }

    # -------------------------------------------------
    # INTENT 0.2 — THANKS (NEW)
    # -------------------------------------------------
    if any(word in message for word in thanks_keywords):
        return {
            "intent": "thanks",
            "reply": (
                "You're very welcome. 🤝\n\n"
                "I'm always here whenever you need help navigating The Mallyard.\n\n"
                "Is there anything else I can assist you with today?"
            )
        }

    # -------------------------------------------------
    # INTENT 0.3 — GOODBYE (NEW)
    # -------------------------------------------------
    if any(word in message for word in goodbye_keywords):
        return {
            "intent": "goodbye",
            "reply": (
                "👋 **Thank you for visiting The Mallyard.**\n\n"
                "I hope you found what you were looking for. If you need anything else, I'm just a message away.\n\n"
                "Have a great day!"
            )
        }

    # -------------------------------------------------
    # INTENT 0.4 — MERCHANT GROWTH HELP (NEW)
    # -------------------------------------------------
    if any(word in message for word in merchant_growth_keywords):
        # How to create a good listing
        if "good listing" in message or "listing tips" in message or "create a good listing" in message:
            reply = (
                "📝 **How to create a good listing:**\n\n"
                "Great listings are clear, complete, and trustworthy.\n\n"
                "**Tips:**\n"
                "• Use a clear product or service title\n"
                "• Add high-quality photos\n"
                "• Write a detailed description\n"
                "• Include important specifications\n"
                "• Set a realistic price\n"
                "• Keep stock information updated\n\n"
                "The more information you provide, the easier it is for customers to trust and buy from you."
            )
        # How to attract more customers
        elif "attract customers" in message or "get customers" in message or "more customers" in message:
            reply = (
                "👥 **How to attract more customers:**\n\n"
                "Customers are more likely to buy from sellers who appear professional and responsive.\n\n"
                "**Try these strategies:**\n"
                "• Use clear product photos\n"
                "• Offer competitive pricing\n"
                "• Respond quickly to inquiries\n"
                "• Keep listings updated\n"
                "• Create multiple listings instead of relying on a single product\n"
                "• Maintain a complete business profile"
            )
        # How to increase sales
        elif "increase sales" in message or "sell more" in message or "boost sales" in message:
            reply = (
                "📈 **How to increase sales:**\n\n"
                "Growing sales takes consistency.\n\n"
                "**Successful merchants often:**\n"
                "• Add new listings regularly\n"
                "• Use attractive product images\n"
                "• Keep products in stock\n"
                "• Offer reliable delivery options\n"
                "• Provide excellent customer service\n"
                "• Build trust through professionalism and communication"
            )
        # Why no orders
        elif "no orders" in message or "not getting orders" in message or "no sales" in message:
            reply = (
                "🤔 **Why am I not getting orders?**\n\n"
                "If your listings are receiving views but not converting into sales, consider:\n\n"
                "• Improving product photos\n"
                "• Reviewing pricing\n"
                "• Expanding your product descriptions\n"
                "• Adding more listings\n"
                "• Ensuring contact and business information is complete\n\n"
                "Customers usually buy from sellers who appear trustworthy and informative."
            )
        # How many photos
        elif "how many photos" in message or "listing photos" in message or "product photos" in message:
            reply = (
                "📸 **How many photos should I use?**\n\n"
                "For best results, use multiple clear photos showing different angles of your product or examples of your service. "
                "High-quality images help customers make purchasing decisions with confidence."
            )
        # Customer trust
        elif "trust seller" in message or "customer trust" in message or "build trust" in message:
            reply = (
                "🛡️ **What makes customers trust a seller?**\n\n"
                "Trust is built through:\n\n"
                "• Complete business information\n"
                "• Clear product descriptions\n"
                "• Accurate pricing\n"
                "• Quality photos\n"
                "• Prompt communication\n"
                "• Reliable order fulfillment\n\n"
                "Professional presentation often leads to higher customer confidence."
            )
        # Daily selling tip
        elif "selling tip" in message or "daily tip" in message or "merchant tip" in message:
            reply = (
                "💡 **Today's Selling Tip:**\n\n"
                "Listings with detailed descriptions generally attract more customer engagement than listings with only a title and price.\n\n"
                "Take time to describe your product or service thoroughly — it builds trust and increases conversion."
            )
        else:
            reply = (
                "📈 **Merchant Success Center**\n\n"
                "**I can help you with:**\n"
                "• How to create a good listing\n"
                "• How to attract more customers\n"
                "• How to increase sales\n"
                "• Why you might not be getting orders\n"
                "• How many photos to use\n"
                "• How to build customer trust\n"
                "• Daily selling tips\n\n"
                "**What would you like to know about growing your business?**"
            )
        
        return {
            "intent": "merchant_growth_help",
            "reply": reply
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
                    "🔐 **Please log in to continue.**\n\n"
                    "Go to the login page and sign in, then I can help you track your orders."
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
                "reply": "📦 You currently have no orders."
            }

        return {
            "intent": "order_tracking",
            "reply": f"📦 Your latest order (#{order.id}) is currently: **{order.status}**"
        }

    # -------------------------------------------------
    # INTENT 1.5 — DELIVERY HELP (NEW)
    # -------------------------------------------------
    if any(word in message for word in delivery_keywords):
        # Sub-intent detection for specific delivery questions
        if "how does delivery work" in message or "delivery process" in message:
            reply = (
                "🚚 **How delivery works on The Mallyard:**\n\n"
                "Delivery is handled through our delivery network and merchant partners. "
                "Once your order is confirmed, it is prepared by the seller and assigned for delivery to your chosen address. "
                "You'll receive updates as your order progresses."
            )
        elif "delivery fee" in message or "delivery cost" in message or "delivery fees" in message:
            reply = (
                "💰 **Delivery fees** are calculated based on factors such as distance, location, and delivery type. "
                "The final delivery cost is displayed before you confirm your order."
            )
        elif "track my delivery" in message or "track delivery" in message or "delivery status" in message:
            if not current_user:
                reply = (
                    "📍 Please log in to track your delivery status. "
                    "Once logged in, you can view your order updates in your orders section."
                )
            else:
                reply = (
                    "📍 You can track your delivery status through your orders section. "
                    "Sandy can also help you check the latest status of your orders when you're logged in."
                )
        elif "how long" in message and "delivery" in message:
            reply = (
                "⏱️ Delivery times depend on the distance between the seller and the delivery location. "
                "Most intra-city deliveries are completed within the same day or the next day, "
                "while inter-city deliveries may take longer depending on the route and logistics availability."
            )
        elif "outside the city" in message or "inter-city" in message:
            reply = (
                "🌍 Yes. The Mallyard supports both intra-city and inter-city deliveries where routes are available. "
                "Delivery availability may vary depending on the seller's location and the destination city."
            )
        else:
            reply = (
                "🚚 **Delivery Information**\n\n"
                "• Delivery is handled by approved delivery partners and merchants\n"
                "• Fees are calculated based on distance and location\n"
                "• Most intra-city deliveries are same-day or next-day\n"
                "• You can track your delivery status in your orders section\n\n"
                "Is there something specific about delivery you'd like to know?"
            )
        
        return {
            "intent": "delivery_help",
            "reply": reply
        }

    # -------------------------------------------------
    # INTENT 1.6 — PAYMENT HELP (NEW)
    # -------------------------------------------------
    if any(word in message for word in payment_keywords):
        # Sub-intent detection for specific payment questions
        if "cash on delivery" in message or "cod" in message:
            reply = (
                "💵 **Cash on Delivery (COD)** is currently one of the primary payment options available on The Mallyard. "
                "Buyers can pay when their order is delivered, subject to seller and delivery availability."
            )
        elif "ecocash" in message:
            reply = (
                "📱 The Mallyard does not currently process EcoCash payments directly through the platform. "
                "However, some buyers and sellers may choose to use EcoCash independently after agreeing on payment arrangements."
            )
        elif "mobile money" in message:
            reply = (
                "📱 The Mallyard does not currently provide built-in mobile money processing. "
                "Buyers and sellers may choose to use mobile money services independently if both parties agree."
            )
        elif "card" in message or "credit card" in message or "debit card" in message:
            reply = (
                "💳 The Mallyard does not currently process card payments directly through the platform. "
                "Any external payment arrangements should only be made with trusted sellers and through secure payment channels."
            )
        elif "currency" in message:
            reply = (
                "💱 Listings may be displayed in different currencies depending on the seller. "
                "Any payment arrangements made outside the platform should be agreed upon between the buyer and seller before payment is made."
            )
        elif "payment protected" in message or "protection" in message or "safe" in message:
            reply = (
                "🛡️ The Mallyard currently facilitates connections between buyers and sellers. "
                "Payments made outside the platform are arranged directly between the buyer and seller. "
                "We recommend confirming all payment details carefully before completing a transaction."
            )
        else:
            reply = (
                "💳 **Payment Methods on The Mallyard**\n\n"
                "• **Cash on Delivery (COD)** is available for eligible orders\n"
                "• Buyers and sellers may also agree on alternative payment methods directly\n"
                "• Available payment arrangements should always be confirmed with the seller before completing a transaction\n\n"
                "**Note:** The Mallyard does not currently process payments directly through the platform. "
                "All payment arrangements are made between buyers and sellers.\n\n"
                "Is there something specific about payments you'd like to know?"
            )
        
        return {
            "intent": "payment_help",
            "reply": reply
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

        if not search_terms:
            return {
                "intent": "buyer_discovery",
                "reply": "I couldn't find that product or service yet. Try searching with a more specific product or service name."
            }

        from sqlalchemy import or_

        # 🔥 IMPROVED: Prefix matching (more precise than contains)
        search_filters = []
        for term in search_terms:
            search_filters.append(Listing.name.ilike(f"{term}%"))
            search_filters.append(Listing.description.ilike(f"{term}%"))
            search_filters.append(Merchant.business_name.ilike(f"{term}%"))

        # Apply SQL filters with limit
        listings = (
            db.query(Listing)
            .join(Merchant, Listing.merchant_id == Merchant.id)
            .filter(or_(*search_filters))
            .limit(20)
            .all()
        )

        matched_results = []
        seen_listing_ids = set()

        # Scoring with improved weights
        for listing in listings:
            listing_name = (listing.name or "").lower()
            listing_description = (listing.description or "").lower()

            score = 0

            for term in search_terms:
                # Exact match (highest weight)
                if term == listing_name:
                    score += 15
                # Name starts with term (strong)
                elif listing_name.startswith(term):
                    score += 10
                # Term in name (moderate)
                elif term in listing_name:
                    score += 5
                # Term in description (lower)
                elif term in listing_description:
                    score += 2

            # 🔥 IMPROVED: Higher minimum score threshold (only quality matches)
            if score >= 5 and listing.id not in seen_listing_ids:
                merchant_name = (
                    listing.merchant.business_name
                    if listing.merchant
                    else "Unknown Seller"
                )

                matched_results.append({
                    "id": listing.id,
                    "text": f"{listing.name} — {listing.currency} {listing.price} — {merchant_name}",
                    "score": score
                })
                seen_listing_ids.add(listing.id)

        # 🔥 IMPROVED: Severely limited category/subcategory fallback
        # Only add if we have FEW results (less than 3) and only add 3 total
        if len(matched_results) < 3:
            fallback_added = 0
            MAX_FALLBACK = 3

            # Category fallback (limited)
            categories = db.query(Category).all()
            for category in categories:
                if fallback_added >= MAX_FALLBACK:
                    break
                category_name = (category.name or "").lower()
                if category_name in message:
                    category_listings = (
                        db.query(Listing)
                        .join(SubCategory, Listing.subcategory_id == SubCategory.id)
                        .filter(SubCategory.category_id == category.id)
                        .limit(MAX_FALLBACK - fallback_added)
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
                            "text": f"{listing.name} — {listing.currency} {listing.price} — {merchant_name}",
                            "score": 3
                        })
                        seen_listing_ids.add(listing.id)
                        fallback_added += 1

            # Subcategory fallback (limited)
            if fallback_added < MAX_FALLBACK:
                subcategories = db.query(SubCategory).all()
                for subcategory in subcategories:
                    if fallback_added >= MAX_FALLBACK:
                        break
                    subcategory_name = (subcategory.name or "").lower()
                    if subcategory_name in message:
                        sub_listings = (
                            db.query(Listing)
                            .filter(Listing.subcategory_id == subcategory.id)
                            .limit(MAX_FALLBACK - fallback_added)
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
                                "text": f"{listing.name} — {listing.currency} {listing.price} — {merchant_name}",
                                "score": 3
                            })
                            seen_listing_ids.add(listing.id)
                            fallback_added += 1

        if matched_results:
            matched_results = sorted(
                matched_results,
                key=lambda item: item["score"],
                reverse=True
            )

            # Limit to top 5 results for cleaner response
            results_text = "\n".join(
                item["text"] for item in matched_results[:5]
            )

            return {
                "intent": "buyer_discovery",
                "reply": f"🔍 I found these products or services:\n\n{results_text}"
            }

        return {
            "intent": "buyer_discovery",
            "reply": "I couldn't find that product or service yet. Try searching with a more specific product or service name."
        }

    # -------------------------------------------------
    # INTENT 3 — GENERAL HELP (NEW - separated from seller help)
    # -------------------------------------------------
    if any(word in message for word in general_help_keywords):
        return {
            "intent": "general_help",
            "reply": (
                "🆘 **How can I help you today?**\n\n"
                "**I can assist with:**\n"
                "• 🔍 Finding products and services\n"
                "• 📦 Tracking your orders\n"
                "• 🏪 Becoming a seller on The Mallyard\n"
                "• 🚚 Delivery information\n"
                "• 💳 Payment questions\n"
                "• 📖 General marketplace questions\n\n"
                "**What would you like help with?**"
            )
        }

    # -------------------------------------------------
    # INTENT 4 — SELLER HELP (Guest-safe)
    # -------------------------------------------------

    if any(word in message for word in seller_keywords) or any(word in message for word in seller_help_keywords):
        return {
            "intent": "seller_help",
            "reply": (
                "✨ **Start selling on The Mallyard**\n\n"
                "We've made it simple, structured, and built for growth.\n\n"
                "👉 **[Register as a Merchant](https://themallyard.com/register/merchant)**\n\n"
                "**Next steps:**\n"
                "1️⃣ Log in and access your dashboard\n"
                "2️⃣ Set up your business (logo, description, contacts)\n"
                "3️⃣ Add your pickup address and city\n"
                "4️⃣ Create listings and start selling\n\n"
                "💡 *Use the sidebar in your dashboard to manage everything easily.*\n\n"
                "🚀 Ready? Tap the link above and launch your store."
            )
        }

    # -------------------------------------------------
    # INTENT 5 — ABOUT THE MALLYARD
    # Guest-safe
    # -------------------------------------------------

    if "mallyard" in message:
        return {
            "intent": "about_mallyard",
            "reply": (
                "🏪 **The Mallyard** is a digital marketplace where customers can discover and purchase products or book services "
                "from trusted local or global merchants and service providers. "
                "It connects buyers with businesses, making it easy to explore groceries, electronics, services, and more "
                "all in one platform. Sellers can create stores, list their products or services, and receive orders or bookings "
                "from customers through the platform.\n\n"
                "Is there something specific you'd like to know about The Mallyard?"
            )
        }

    # -------------------------------------------------
    # IMPROVED FALLBACK
    # -------------------------------------------------

    return {
        "intent": "unknown",
        "reply": (
            "🤔 **I'm not sure I understood that.**\n\n"
            "**I can help you with:**\n"
            "• 🔍 Finding products and services — try *'find a laptop'* or *'show me plumbers'*\n"
            "• 📦 Tracking your orders — try *'track my order'*\n"
            "• 🏪 Starting to sell — try *'how to become a merchant'*\n"
            "• 🚚 Delivery questions — try *'how does delivery work'*\n"
            "• 💳 Payment questions — try *'what payment methods are accepted'*\n"
            "• 📈 Growing your business — try *'how to increase sales'* or *'selling tip'*\n\n"
            "**What would you like to do?**"
        )
    }