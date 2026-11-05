"""Unit tests for PricingService unit economics and financial reconciliation (TSK-P7-001)."""

import pytest
from app.services.pricing_service import PricingService


def test_standard_booking_quote_reconciliation():
    """Verify exact Rs 91.80 breakdown matches PRD and ledger template 1."""
    # 2 hours @ Rs 40.00/hr = Rs 80.00 base
    quote = PricingService.calculate_booking_quote(
        base_rate_per_hour_inr=40.0,
        duration_hours=2.0,
    )

    assert quote["gross_parking_base_inr"] == 80.00
    assert quote["convenience_fee_inr"] == 10.00
    assert quote["gst_convenience_inr"] == 1.80
    assert quote["total_driver_paid_inr"] == 91.80

    # Host deductions
    assert quote["platform_commission_inr"] == 12.00
    assert quote["gst_commission_inr"] == 2.16
    assert quote["total_host_deductions_inr"] == 14.16

    # Net host entitlement
    assert quote["owner_net_entitlement_inr"] == 65.84

    # Processing and taxes
    assert quote["gateway_mdr_inr"] == 2.17
    assert quote["gst_output_liability_inr"] == 3.96

    # Net platform margin: (12.00 + 10.00) - 2.17 = 19.83
    assert quote["platform_net_margin_inr"] == 19.83

    # Exact zero discrepancy check
    assert quote["discrepancy_inr"] == 0.00
    assert quote["total_allocated_inr"] == 91.80

    # Paise allocations for ledger
    paise = quote["paise"]
    assert paise["total_driver_paid"] == 9180
    assert paise["owner_net_entitlement"] == 6584
    assert paise["platform_net_margin"] == 1983
    assert paise["gst_output_liability"] == 396
    assert paise["gateway_mdr"] == 217
    assert paise["owner_net_entitlement"] + paise["platform_net_margin"] + paise["gst_output_liability"] + paise["gateway_mdr"] == 9180


def test_custom_pricing_quote():
    """Verify arbitrary pricing inputs maintain exact zero-discrepancy invariant."""
    test_cases = [
        (25.50, 3.5),
        (100.0, 1.0),
        (15.0, 8.0),
        (45.0, 24.0),
    ]

    for rate, hours in test_cases:
        quote = PricingService.calculate_booking_quote(rate, hours)
        assert quote["discrepancy_inr"] == 0.00
        assert quote["total_driver_paid_inr"] == quote["total_allocated_inr"]
        assert quote["owner_net_entitlement_inr"] > 0
        assert quote["platform_net_margin_inr"] > 0
