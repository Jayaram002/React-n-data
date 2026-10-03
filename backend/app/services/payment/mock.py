import uuid
from typing import Dict, Any
from app.services.payment.base import BasePaymentProvider

class MockPaymentProvider(BasePaymentProvider):
    def create_order(self, order_id: int, amount_paise: int, currency: str = "INR") -> Dict[str, Any]:
        return {
            "provider": "mock",
            "provider_ref": f"mock_order_{order_id}_{uuid.uuid4().hex[:8]}",
            "amount_paise": amount_paise,
            "currency": currency,
            "checkout_url": f"/mock-checkout/{order_id}"
        }

    def verify_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Mock verification always validates true
        return {
            "verified": True,
            "provider_payment_id": payload.get("provider_payment_id", f"mock_pay_{uuid.uuid4().hex[:8]}"),
            "status": payload.get("status", "completed")
        }

    def refund(self, payment_ref: str, amount_paise: int) -> Dict[str, Any]:
        return {
            "provider": "mock",
            "refund_ref": f"mock_ref_{uuid.uuid4().hex[:8]}",
            "amount_paise": amount_paise,
            "status": "completed"
        }

    def payout(self, payout_request_id: int, amount_paise: int, destination_account: str) -> Dict[str, Any]:
        return {
            "provider": "mock",
            "payout_ref": f"mock_payout_{payout_request_id}_{uuid.uuid4().hex[:8]}",
            "amount_paise": amount_paise,
            "status": "completed"
        }
