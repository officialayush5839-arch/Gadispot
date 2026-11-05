"""Unit tests for CompatibilityService dimensional clearance and EV matching (TSK-P7-001)."""

import pytest
from app.services.compatibility_service import (
    CompatibilityService,
    VehicleDimensions,
    SpaceDimensions,
)


def test_compatible_hatchback_in_standard_bay():
    """Verify hatchback fits with adequate margins."""
    # Maruti Swift: 3845mm L, 1735mm W, 1530mm H
    vehicle = VehicleDimensions(
        length_mm=3845,
        width_mm=1735,
        height_mm=1530,
        is_ev=False,
    )
    # Standard Bay: 5000mm L, 2400mm W, 2100mm H
    space = SpaceDimensions(
        length_mm=5000,
        width_mm=2400,
        height_mm=2100,
        is_ev_charging=False,
    )

    result = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert result.is_compatible is True
    assert result.length_clearance_mm >= 300
    assert result.width_clearance_mm >= 400
    assert result.height_clearance_mm >= 100
    assert len(result.rejection_reasons) == 0


def test_oversized_suv_rejected():
    """Verify Toyota Fortuner fails in undersized compact bay."""
    # Toyota Fortuner: 4795mm L, 1855mm W, 1835mm H
    vehicle = VehicleDimensions(
        length_mm=4795,
        width_mm=1855,
        height_mm=1835,
        is_ev=False,
    )
    # Compact Bay: 4900mm L (need 4795+300=5095mm), 2100mm W (need 1855+400=2255mm)
    space = SpaceDimensions(
        length_mm=4900,
        width_mm=2100,
        height_mm=2000,
        is_ev_charging=False,
    )

    result = CompatibilityService.evaluate_compatibility(vehicle, space)
    assert result.is_compatible is False
    assert len(result.rejection_reasons) == 2
    assert "Insufficient length clearance" in result.rejection_reasons[0]
    assert "Insufficient width clearance" in result.rejection_reasons[1]


def test_ev_charging_requirement_enforcement():
    """Verify EV vehicle requires is_ev_charging=True on space."""
    vehicle = VehicleDimensions(
        length_mm=3800,
        width_mm=1700,
        height_mm=1500,
        is_ev=True,
    )
    # Non-EV space
    space_no_ev = SpaceDimensions(
        length_mm=5000,
        width_mm=2400,
        height_mm=2100,
        is_ev_charging=False,
    )
    res_no_ev = CompatibilityService.evaluate_compatibility(vehicle, space_no_ev)
    assert res_no_ev.is_compatible is False
    assert "EV vehicle requires dedicated charging bay" in res_no_ev.rejection_reasons[0]

    # EV space
    space_with_ev = SpaceDimensions(
        length_mm=5000,
        width_mm=2400,
        height_mm=2100,
        is_ev_charging=True,
    )
    res_ev = CompatibilityService.evaluate_compatibility(vehicle, space_with_ev)
    assert res_ev.is_compatible is True
