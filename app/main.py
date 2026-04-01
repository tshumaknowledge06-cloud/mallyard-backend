from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.db.init_db import init_db
from fastapi import Request

# 🔹 Import routers
from app.api.routes import auth
from app.api.routes import test_rbac
from app.api.routes import merchant
from app.api.routes import users
from app.api.routes import category
from app.api.routes import subcategory
from app.api.routes import listings
from app.api.routes import sandy
from app.api.routes import delivery
from app.api.routes import delivery_request
from app.api.routes import delivery_match
from app.api.routes import orders
from app.api.routes import booking
from app.api.routes import wishlist
from app.api.routes import recently_viewed
from app.api.routes import trending
from app.api.routes import admin_analytics
from app.api.routes import cart
from app.api.routes import review
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="The Mallyard API")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Slow down."},
    )

init_db()

origins = os.getenv("CORS_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request
from fastapi.responses import Response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data: https:; script-src 'self'; style-src 'self' 'unsafe-inline'"

    return response

# ✅ Ensure upload folders exist
os.makedirs("uploads/listings", exist_ok=True)
os.makedirs("uploads/delivery", exist_ok=True)
os.makedirs("uploads/merchants", exist_ok=True)

# ✅ Serve uploaded files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ✅ Routers (AFTER mount)
app.include_router(auth.router)
app.include_router(test_rbac.router)
app.include_router(users.router)
app.include_router(merchant.router)
app.include_router(category.router)
app.include_router(subcategory.router)
app.include_router(listings.router, prefix="/listings")
app.include_router(sandy.router)
app.include_router(delivery.router)
app.include_router(delivery_request.router)
app.include_router(delivery_match.router)
app.include_router(orders.router)
app.include_router(booking.router, tags=["Bookings"])
app.include_router(wishlist.router)
app.include_router(recently_viewed.router)
app.include_router(trending.router)
app.include_router(admin_analytics.router)
app.include_router(cart.router)
app.include_router(review.router)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Slow down."},
    )


