"""Payment Gateway Factory for runtime-swappable gateway adapters."""

from typing import Dict
from app.core.config import get_settings
from app.core.exceptions import ValidationException
from app.integrations.payments.base import PaymentGatewayPort
from app.integrations.payments.cashfree_adapter import CashfreeAdapter
from app.integrations.payments.demo_adapter import DemoPaymentAdapter
from app.integrations.payments.hyperswitch_adapter import HyperswitchAdapter
from app.integrations.payments.razorpay_adapter import RazorpayAdapter
from app.integrations.payments.youpi_adapter import YoupiPaymentAdapter


class PaymentGatewayFactory:
    """Factory creating and resolving payment gateway adapters with security guards."""

    @staticmethod
    def get_adapter(gateway_name: str | None = None) -> PaymentGatewayPort:
        settings = get_settings()
        target = (gateway_name or settings.PAYMENT_MODE).lower().strip()

        if target == "demo":
            if settings.is_production:
                raise ValidationException(
                    detail="Demo payment mode is strictly forbidden in production.",
                    code="DEMO_MODE_FORBIDDEN",
                )
            return DemoPaymentAdapter(is_enabled=settings.DEMO_PAYMENTS_ENABLED)

        elif target == "youpi":
            if not settings.YOUPI_ENABLED:
                raise ValidationException(
                    detail="Experimental YOUPI-PG adapter is currently disabled. Set YOUPI_ENABLED=true to enable.",
                    code="YOUPI_ADAPTER_DISABLED",
                )
            return YoupiPaymentAdapter(
                base_url=settings.YOUPI_BASE_URL,
                api_key=settings.YOUPI_API_KEY,
                webhook_secret=settings.YOUPI_WEBHOOK_SECRET,
                is_enabled=True,
            )

        elif target == "razorpay":
            return RazorpayAdapter(
                key_id=settings.RAZORPAY_KEY_ID or None,
                key_secret=settings.RAZORPAY_KEY_SECRET or None,
                webhook_secret=settings.RAZORPAY_WEBHOOK_SECRET or None,
            )

        elif target == "cashfree":
            return CashfreeAdapter(
                app_id=settings.CASHFREE_APP_ID or None,
                secret_key=settings.CASHFREE_SECRET_KEY or None,
            )

        elif target == "hyperswitch":
            return HyperswitchAdapter()

        else:
            raise ValidationException(
                detail=f"Unsupported payment gateway: '{target}'. Supported: {PaymentGatewayFactory.get_supported_gateways()}",
                code="UNSUPPORTED_GATEWAY",
            )

    @staticmethod
    def get_supported_gateways() -> list[str]:
        settings = get_settings()
        gateways = ["razorpay", "cashfree", "hyperswitch"]
        if not settings.is_production and settings.DEMO_PAYMENTS_ENABLED:
            gateways.insert(0, "demo")
        if settings.YOUPI_ENABLED:
            gateways.append("youpi")
        return gateways
