from app.core.config import settings
from app.services.payment.base import BasePaymentProvider
from app.services.payment.mock import MockPaymentProvider

_payment_instance: BasePaymentProvider = None

def get_payment_provider() -> BasePaymentProvider:
    global _payment_instance
    if _payment_instance is None:
        # Currently mock provider is selected
        _payment_instance = MockPaymentProvider()
    return _payment_instance
