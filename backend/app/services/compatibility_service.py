"""Vehicle-Bay physical clearance and capability compatibility engine (FR-INVENTORY-001).

Calculates 3D clearance margins:
- Length: +300mm (+0.3m)
- Width:  +400mm (+0.4m)
- Height: +100mm (+0.1m)
- EV charging capability requirement check
"""

from pydantic import BaseModel


class VehicleDimensions(BaseModel):
    length_mm: int
    width_mm: int
    height_mm: int
    is_ev: bool = False


class SpaceDimensions(BaseModel):
    length_mm: int
    width_mm: int
    height_mm: int
    is_ev_charging: bool = False


class CompatibilityResult(BaseModel):
    is_compatible: bool
    length_clearance_mm: int
    width_clearance_mm: int
    height_clearance_mm: int
    rejection_reasons: list[str]


class CompatibilityService:
    """Evaluates whether a vehicle fits into a parking space."""

    REQUIRED_LENGTH_CLEARANCE_MM = 300  # +0.3m
    REQUIRED_WIDTH_CLEARANCE_MM = 400  # +0.4m
    REQUIRED_HEIGHT_CLEARANCE_MM = 100  # +0.1m

    @classmethod
    def evaluate_compatibility(
        cls,
        vehicle: VehicleDimensions,
        space: SpaceDimensions,
    ) -> CompatibilityResult:
        """Evaluate multidimensional vehicle-to-space compatibility."""
        rejection_reasons: list[str] = []

        length_clearance = space.length_mm - vehicle.length_mm
        width_clearance = space.width_mm - vehicle.width_mm
        height_clearance = space.height_mm - vehicle.height_mm

        if length_clearance < cls.REQUIRED_LENGTH_CLEARANCE_MM:
            rejection_reasons.append(
                f"Insufficient length clearance: {length_clearance}mm available, "
                f"{cls.REQUIRED_LENGTH_CLEARANCE_MM}mm required."
            )

        if width_clearance < cls.REQUIRED_WIDTH_CLEARANCE_MM:
            rejection_reasons.append(
                f"Insufficient width clearance: {width_clearance}mm available, "
                f"{cls.REQUIRED_WIDTH_CLEARANCE_MM}mm required."
            )

        if height_clearance < cls.REQUIRED_HEIGHT_CLEARANCE_MM:
            rejection_reasons.append(
                f"Insufficient height clearance: {height_clearance}mm available, "
                f"{cls.REQUIRED_HEIGHT_CLEARANCE_MM}mm required."
            )

        if vehicle.is_ev and not space.is_ev_charging:
            rejection_reasons.append("EV vehicle requires dedicated charging bay (is_ev_charging=True).")

        return CompatibilityResult(
            is_compatible=len(rejection_reasons) == 0,
            length_clearance_mm=length_clearance,
            width_clearance_mm=width_clearance,
            height_clearance_mm=height_clearance,
            rejection_reasons=rejection_reasons,
        )
