from fastapi import APIRouter
from app.api.v1 import auth, categories, uploads, listings, orders, mock_payments, earnings, payouts, admin

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(uploads.router)
api_router.include_router(listings.router)
api_router.include_router(orders.router)
api_router.include_router(mock_payments.router)
api_router.include_router(earnings.router)
api_router.include_router(payouts.router)
api_router.include_router(admin.router)


