from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BasePaymentProvider(ABC):
    @abstractmethod
    def create_order(self, order_id: int, amount_paise: int, currency: str = "INR") -> Dict[str, Any]:
        """Creates payment order with provider"""
        pass

    @abstractmethod
    def verify_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Verifies payment signature and status"""
        pass

    @abstractmethod
    def refund(self, payment_ref: str, amount_paise: int) -> Dict[str, Any]:
        """Initiates refund with provider"""
        pass

    @abstractmethod
    def payout(self, payout_request_id: int, amount_paise: int, destination_account: str) -> Dict[str, Any]:
        """Initiates payout to contributor"""
        pass
