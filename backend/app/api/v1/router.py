from fastapi import APIRouter

from app.api.v1.endpoints import (
    access,
    auth,
    bookings,
    health,
    ops,
    payments,
    properties,
    webhooks,
)

api_router = APIRouter()

# Health endpoints under /api/v1/health (e.g. /api/v1/health, /api/v1/health/live, /api/v1/health/ready)
api_router.include_router(health.router, prefix="/health", tags=["Health & Diagnostics"])

# Authentication & 2FA endpoints under /api/v1/auth
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & 2FA"])

# Booking holds & reservations under /api/v1/bookings
api_router.include_router(bookings.router, prefix="/bookings", tags=["Bookings & Holds"])

# Payment Webhook ingestion under /api/v1/webhooks
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Payment Webhooks"])

# Payment Management & UPI QR under /api/v1/payments
api_router.include_router(payments.router, prefix="/payments", tags=["Payment Management & UPI QR"])

# Gate Access Pass Issuance & Verification under /api/v1/access
api_router.include_router(access.router, prefix="/access", tags=["Gate Access Passes"])

# Property & Inventory Management under /api/v1/properties
api_router.include_router(properties.router, prefix="/properties", tags=["Property & Inventory Management"])

# Parking Spaces under /api/v1/spaces
api_router.include_router(properties.spaces_router, prefix="/spaces", tags=["Property & Inventory Management"])

# Operations Review & Verification under /api/v1/ops
api_router.include_router(ops.router, prefix="/ops", tags=["Operations & Property Review"])
