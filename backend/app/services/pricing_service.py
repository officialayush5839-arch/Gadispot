"""Pricing and unit economics calculation service for Gadispot.

Enforces exact financial reconciliation according to PRD V2.3.2 and PAYMENT_AND_LEDGER_DESIGN.md:
Driver Inflow = Owner Entitlement + Platform Net Margin + GST Output Liability + Gateway MDR.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def round_inr(val: Decimal) -> Decimal:
    """Standard 2-decimal half-up rounding for INR calculations."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class PricingService:
    """Computes exact booking quotes, fee splits, and ledger allocations."""

    DEFAULT_COMMISSION_RATE = Decimal("0.15")  # 15% Platform Commission
    DEFAULT_GST_RATE = Decimal("0.18")  # 18% GST (CGST 9% + SGST 9%)
    DEFAULT_CONVENIENCE_FEE = Decimal("10.00")  # ₹10 Convenience Fee
    DEFAULT_MDR_RATE = Decimal("0.0236")  # 2.36% (2% MDR + 18% GST on MDR)

    @classmethod
    def calculate_booking_quote(
        cls,
        base_rate_per_hour_inr: float | Decimal,
        duration_hours: float | Decimal,
        commission_rate: float | Decimal = DEFAULT_COMMISSION_RATE,
        gst_rate: float | Decimal = DEFAULT_GST_RATE,
        convenience_fee_inr: float | Decimal = DEFAULT_CONVENIENCE_FEE,
        mdr_rate: float | Decimal = DEFAULT_MDR_RATE,
    ) -> dict[str, Any]:
        """Compute exact financial breakdown in INR and paise."""
        rate = Decimal(str(base_rate_per_hour_inr))
        hours = Decimal(str(duration_hours))
        c_rate = Decimal(str(commission_rate))
        t_rate = Decimal(str(gst_rate))
        conv_fee = Decimal(str(convenience_fee_inr))
        m_rate = Decimal(str(mdr_rate))

        # 1. Driver Inflow
        gross_parking_base = round_inr(rate * hours)
        gst_convenience = round_inr(conv_fee * t_rate)
        total_driver_paid = round_inr(gross_parking_base + conv_fee + gst_convenience)

        # 2. Platform Commission & Host Facilitation
        platform_commission = round_inr(gross_parking_base * c_rate)
        gst_commission = round_inr(platform_commission * t_rate)
        total_host_deductions = round_inr(platform_commission + gst_commission)

        # 3. Property Owner Net Entitlement
        owner_net_entitlement = round_inr(gross_parking_base - total_host_deductions)

        # 4. Gateway Processing (Absorbed by platform)
        gateway_mdr = round_inr(total_driver_paid * m_rate)

        # 5. GST Output Tax Liability (Account 2030)
        gst_output_liability = round_inr(gst_convenience + gst_commission)

        # 6. Platform Net Operating Margin (P&L contribution)
        platform_net_margin = round_inr((platform_commission + conv_fee) - gateway_mdr)

        # 7. Cash Flow Reconciliation Check
        total_allocated = round_inr(owner_net_entitlement + platform_net_margin + gst_output_liability + gateway_mdr)
        discrepancy = round_inr(total_driver_paid - total_allocated)

        return {
            "gross_parking_base_inr": float(gross_parking_base),
            "convenience_fee_inr": float(conv_fee),
            "gst_convenience_inr": float(gst_convenience),
            "total_driver_paid_inr": float(total_driver_paid),
            "platform_commission_inr": float(platform_commission),
            "gst_commission_inr": float(gst_commission),
            "total_host_deductions_inr": float(total_host_deductions),
            "owner_net_entitlement_inr": float(owner_net_entitlement),
            "gateway_mdr_inr": float(gateway_mdr),
            "gst_output_liability_inr": float(gst_output_liability),
            "platform_net_margin_inr": float(platform_net_margin),
            "total_allocated_inr": float(total_allocated),
            "discrepancy_inr": float(discrepancy),
            # Paise equivalents for General Ledger journal lines
            "paise": {
                "total_driver_paid": int(total_driver_paid * 100),
                "owner_net_entitlement": int(owner_net_entitlement * 100),
                "platform_net_margin": int(platform_net_margin * 100),
                "gst_output_liability": int(gst_output_liability * 100),
                "gateway_mdr": int(gateway_mdr * 100),
            },
        }
