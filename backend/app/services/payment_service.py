"""Core Payment Service orchestrating reservations, pricing, payment gateways, and ledger postings."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
import secrets
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConflictException,
    EntityNotFoundException,
    ForbiddenException,
    ValidationException,
)
from app.integrations.payments.factory import PaymentGatewayFactory
from app.models.access import AccessCredential
from app.models.enums import (
    EntrySideEnum,
    JournalStatusEnum,
    PaymentProviderEnum,
    PaymentStatusEnum,
    ReservationStatusEnum,
    TokenStatusEnum,
    TokenTypeEnum,
)
from app.models.ledger import JournalEntry, JournalLine
from app.models.parking import ParkingSpace
from app.models.payments import Payment
from app.models.reservations import SpaceReservation
from app.services.pricing_service import PricingService

logger = logging.getLogger("gadispot.payments")


class PaymentService:
    """Orchestrates payment order creation, simulated execution, access token minting, and double-entry ledger balance."""

    @classmethod
    async def create_payment(
        cls,
        db: AsyncSession,
        reservation_id: uuid.UUID,
        driver_id: uuid.UUID,
        gateway_name: str = "demo",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a payment intent/order for an active reservation hold."""
        # 1. Deduplication via idempotency key
        if idempotency_key:
            stmt_idem = select(Payment).where(Payment.idempotency_key == idempotency_key)
            existing_payment = (await db.execute(stmt_idem)).scalar_one_or_none()
            if existing_payment:
                return {
                    "payment": existing_payment,
                    "order_id": existing_payment.provider_order_id,
                    "amount_paise": existing_payment.amount_paise,
                    "status": existing_payment.status.value,
                    "quote": existing_payment.payment_metadata.get("quote"),
                    "is_simulated": existing_payment.is_simulated,
                }

        # 2. Fetch and lock reservation
        stmt_res = select(SpaceReservation).where(SpaceReservation.id == reservation_id).with_for_update()
        res_result = await db.execute(stmt_res)
        reservation = res_result.scalar_one_or_none()
        if not reservation:
            raise EntityNotFoundException(
                detail=f"Reservation {reservation_id} not found",
                code="RESERVATION_NOT_FOUND",
            )

        # 3. Security: Caller must be the driver
        if reservation.driver_id != driver_id:
            raise ForbiddenException(
                detail="You do not have permission to pay for this reservation",
                code="FORBIDDEN_RESERVATION_PAYMENT",
            )

        # 4. State validation
        if reservation.status != ReservationStatusEnum.ACTIVE_HOLD:
            raise ValidationException(
                detail=f"Cannot initiate payment for reservation in status {reservation.status.value}",
                code="INVALID_RESERVATION_STATUS",
            )

        # 5. Check hold expiration
        now = datetime.now(timezone.utc)
        if reservation.hold_expires_at and reservation.hold_expires_at < now:
            reservation.status = ReservationStatusEnum.EXPIRED
            await db.flush()
            raise ValidationException(
                detail="The 480-second checkout hold for this reservation has expired",
                code="HOLD_EXPIRED",
            )

        # 6. Fetch parking space to compute accurate quote
        stmt_space = select(ParkingSpace).where(ParkingSpace.id == reservation.parking_space_id)
        space = (await db.execute(stmt_space)).scalar_one_or_none()
        if not space:
            raise EntityNotFoundException(
                detail=f"Parking space {reservation.parking_space_id} not found",
                code="PARKING_SPACE_NOT_FOUND",
            )

        # 7. Compute pricing breakdown via PricingService
        time_diff = reservation.time_window.upper - reservation.time_window.lower
        duration_hours = max(Decimal("1.0"), Decimal(str(time_diff.total_seconds() / 3600.0)))
        base_rate_per_hour = Decimal(str(space.base_hourly_rate_paise)) / Decimal("100")
        quote = PricingService.calculate_booking_quote(
            base_rate_per_hour_inr=base_rate_per_hour,
            duration_hours=duration_hours,
        )
        total_driver_paise = quote["paise"]["total_driver_paid"]

        # 8. Obtain payment gateway adapter
        adapter = PaymentGatewayFactory.get_adapter(gateway_name)
        receipt_id = f"rcpt_{reservation.booking_reference}"
        order_res = await adapter.create_order(
            amount_paise=total_driver_paise,
            receipt=receipt_id,
            currency="INR",
            notes={
                "reservation_id": str(reservation.id),
                "driver_id": str(driver_id),
                "booking_reference": reservation.booking_reference,
            },
        )

        # 9. Map provider enum
        provider_key = gateway_name.upper().strip()
        try:
            provider_enum = PaymentProviderEnum[provider_key]
        except KeyError:
            provider_enum = PaymentProviderEnum.DEMO

        # 10. Persist Payment entity
        payment = Payment(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            driver_id=driver_id,
            amount_paise=total_driver_paise,
            currency="INR",
            provider=provider_enum,
            provider_payment_id=None,
            provider_order_id=order_res.order_id,
            status=PaymentStatusEnum.CREATED,
            is_simulated=(provider_enum == PaymentProviderEnum.DEMO),
            is_experimental=(provider_enum == PaymentProviderEnum.YOUPI),
            experimental_status=None,
            idempotency_key=idempotency_key,
            simulation_scenario=None,
            failure_reason=None,
            payment_metadata={"quote": quote, "breakdown": quote["paise"]},
        )
        db.add(payment)

        # Associate order ID with reservation
        reservation.payment_order_id = order_res.order_id
        await db.flush()

        return {
            "payment": payment,
            "order_id": order_res.order_id,
            "amount_paise": total_driver_paise,
            "currency": "INR",
            "status": payment.status.value,
            "quote": quote,
            "is_simulated": payment.is_simulated,
            "is_experimental": payment.is_experimental,
        }

    @classmethod
    async def complete_demo_payment(
        cls,
        db: AsyncSession,
        payment_id: uuid.UUID,
        driver_id: uuid.UUID,
        outcome: str = "SUCCESS",
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Execute a simulated payment outcome. Strictly prohibited in production environments."""
        # 1. Fail-closed guard: Disallow demo simulation in production
        if settings.is_production or not settings.DEMO_PAYMENTS_ENABLED:
            raise ForbiddenException(
                detail="Simulated payments are strictly forbidden in production environments.",
                code="DEMO_PAYMENTS_FORBIDDEN",
            )

        # 2. Fetch and lock Payment
        stmt_pay = select(Payment).where(Payment.id == payment_id).with_for_update()
        payment = (await db.execute(stmt_pay)).scalar_one_or_none()
        if not payment:
            raise EntityNotFoundException(
                detail=f"Payment {payment_id} not found",
                code="PAYMENT_NOT_FOUND",
            )

        # 3. Ownership validation
        if payment.driver_id != driver_id:
            raise ForbiddenException(
                detail="You do not own this payment transaction",
                code="FORBIDDEN_PAYMENT_ACCESS",
            )

        # 4. Must be a simulated payment
        if not payment.is_simulated or payment.provider != PaymentProviderEnum.DEMO:
            raise ValidationException(
                detail="Only demo simulated payments can be executed via the simulation trigger",
                code="NOT_A_DEMO_PAYMENT",
            )

        # 5. Idempotent short-circuit if already succeeded
        if payment.status == PaymentStatusEnum.SUCCEEDED:
            if outcome.upper() == "SUCCESS":
                return {
                    "payment_id": payment.id,
                    "reservation_id": payment.reservation_id,
                    "status": payment.status.value,
                    "is_simulated": payment.is_simulated,
                    "message": "Payment has already succeeded (idempotent replay)",
                }
            raise ConflictException(
                detail="Cannot alter an already succeeded payment",
                code="PAYMENT_ALREADY_SUCCEEDED",
            )

        # 6. Dispatch to DemoPaymentAdapter
        adapter = PaymentGatewayFactory.get_adapter("demo")
        sim_res = await adapter.simulate_outcome(
            order_id=payment.provider_order_id or str(payment.id),
            outcome=outcome,
            reason=reason,
        )

        # 7. Lock reservation
        stmt_res = select(SpaceReservation).where(SpaceReservation.id == payment.reservation_id).with_for_update()
        reservation = (await db.execute(stmt_res)).scalar_one_or_none()
        if not reservation:
            raise EntityNotFoundException(
                detail=f"Reservation {payment.reservation_id} not found",
                code="RESERVATION_NOT_FOUND",
            )

        now = datetime.now(timezone.utc)
        outcome_upper = outcome.upper().strip()

        if outcome_upper == "SUCCESS":
            payment.status = PaymentStatusEnum.SUCCEEDED
            payment.provider_payment_id = sim_res["payment_id"]
            payment.simulation_scenario = "SUCCESS"
            reservation.status = ReservationStatusEnum.CONFIRMED
            reservation.payment_transaction_id = sim_res["payment_id"]

            # Mint 128-bit CSPRNG access credentials if not already issued
            stmt_cred = select(AccessCredential).where(AccessCredential.reservation_id == reservation.id)
            existing_creds = (await db.execute(stmt_cred)).scalars().all()
            if not existing_creds:
                valid_from = now - timedelta(minutes=15)
                valid_until = now + timedelta(hours=24)
                entry_cred = AccessCredential(
                    id=uuid.uuid4(),
                    reservation_id=reservation.id,
                    token_type=TokenTypeEnum.ENTRY,
                    opaque_token=f"spx_ent_{secrets.token_hex(16)}",
                    status=TokenStatusEnum.ISSUED,
                    valid_from=valid_from,
                    valid_until=valid_until,
                )
                exit_cred = AccessCredential(
                    id=uuid.uuid4(),
                    reservation_id=reservation.id,
                    token_type=TokenTypeEnum.EXIT,
                    opaque_token=f"spx_ext_{secrets.token_hex(16)}",
                    status=TokenStatusEnum.ISSUED,
                    valid_from=valid_from,
                    valid_until=valid_until,
                )
                db.add(entry_cred)
                db.add(exit_cred)

            # Post double-entry balanced general ledger journal entry
            j_ref = f"PAY-{payment.id}"
            stmt_j = select(JournalEntry).where(JournalEntry.transaction_reference == j_ref)
            existing_j = (await db.execute(stmt_j)).scalar_one_or_none()

            if not existing_j:
                journal = JournalEntry(
                    id=uuid.uuid4(),
                    journal_number=f"JN-DEMO-{secrets.token_hex(4).upper()}",
                    transaction_reference=j_ref,
                    transaction_type="PARKING_PAYMENT",
                    currency="INR",
                    posting_status=JournalStatusEnum.DRAFT,
                    description=f"Simulated payment for reservation {reservation.booking_reference}",
                )
                db.add(journal)
                await db.flush()

                metadata = payment.payment_metadata or {}
                quote = metadata.get("quote", {})
                paise = quote.get("paise") or metadata.get("breakdown")

                if not paise:
                    total_paise = payment.amount_paise
                    owner_paise = int(total_paise * 0.85)
                    plat_paise = total_paise - owner_paise
                    lines = [
                        JournalLine(
                            id=uuid.uuid4(),
                            journal_id=journal.id,
                            line_number=1,
                            account_code="1010",
                            entry_side=EntrySideEnum.DEBIT,
                            amount_in_paise=total_paise,
                            description="Debit Gateway Transit Asset for driver payment inflow",
                        ),
                        JournalLine(
                            id=uuid.uuid4(),
                            journal_id=journal.id,
                            line_number=2,
                            account_code="2010",
                            entry_side=EntrySideEnum.CREDIT,
                            amount_in_paise=owner_paise,
                            description=f"Credit Owner Payable Liability for {reservation.booking_reference}",
                        ),
                        JournalLine(
                            id=uuid.uuid4(),
                            journal_id=journal.id,
                            line_number=3,
                            account_code="3010",
                            entry_side=EntrySideEnum.CREDIT,
                            amount_in_paise=plat_paise,
                            description="Credit Platform Commission Revenue",
                        ),
                    ]
                else:
                    total_paise = paise["total_driver_paid"]
                    owner_paise = paise["owner_net_entitlement"]
                    comm_inr = quote.get("platform_commission_inr", 0.0)
                    conv_inr = quote.get("convenience_fee_inr", 0.0)
                    comm_paise = int(round(comm_inr * 100))
                    conv_paise = int(round(conv_inr * 100))
                    gst_paise = paise["gst_output_liability"]

                    # Balance adjustment check
                    credit_sum = owner_paise + comm_paise + conv_paise + gst_paise
                    diff = total_paise - credit_sum
                    if diff != 0:
                        comm_paise += diff

                    lines = [
                        JournalLine(
                            id=uuid.uuid4(),
                            journal_id=journal.id,
                            line_number=1,
                            account_code="1010",
                            entry_side=EntrySideEnum.DEBIT,
                            amount_in_paise=total_paise,
                            description="Debit Gateway Transit Asset (Driver Inflow)",
                        ),
                        JournalLine(
                            id=uuid.uuid4(),
                            journal_id=journal.id,
                            line_number=2,
                            account_code="2010",
                            entry_side=EntrySideEnum.CREDIT,
                            amount_in_paise=owner_paise,
                            description=f"Credit Owner Payable Liability for {reservation.booking_reference}",
                        ),
                        JournalLine(
                            id=uuid.uuid4(),
                            journal_id=journal.id,
                            line_number=3,
                            account_code="3010",
                            entry_side=EntrySideEnum.CREDIT,
                            amount_in_paise=comm_paise,
                            description="Credit Platform Commission Revenue",
                        ),
                        JournalLine(
                            id=uuid.uuid4(),
                            journal_id=journal.id,
                            line_number=4,
                            account_code="3020",
                            entry_side=EntrySideEnum.CREDIT,
                            amount_in_paise=conv_paise,
                            description="Credit Driver Convenience Fee Revenue",
                        ),
                        JournalLine(
                            id=uuid.uuid4(),
                            journal_id=journal.id,
                            line_number=5,
                            account_code="2030",
                            entry_side=EntrySideEnum.CREDIT,
                            amount_in_paise=gst_paise,
                            description="Credit GST Output Tax Payable",
                        ),
                    ]

                for line in lines:
                    db.add(line)
                await db.flush()

                # Transition journal to POSTED (database trigger verifies balance)
                journal.posting_status = JournalStatusEnum.POSTED
                await db.flush()

        elif outcome_upper == "FAILURE":
            payment.status = PaymentStatusEnum.FAILED
            payment.failure_reason = reason or "Simulated test failure"
            payment.simulation_scenario = "FAILURE"

        elif outcome_upper == "CANCEL":
            payment.status = PaymentStatusEnum.CANCELLED
            payment.failure_reason = reason or "Simulated payment cancellation by user"
            payment.simulation_scenario = "CANCEL"

        elif outcome_upper == "TIMEOUT":
            payment.status = PaymentStatusEnum.EXPIRED
            payment.failure_reason = reason or "Simulated checkout timeout"
            payment.simulation_scenario = "TIMEOUT"
            if reservation.hold_expires_at and reservation.hold_expires_at <= now:
                reservation.status = ReservationStatusEnum.EXPIRED

        else:
            raise ValidationException(
                detail=f"Unsupported simulation outcome '{outcome}'. Expected: SUCCESS, FAILURE, CANCEL, TIMEOUT",
                code="INVALID_SIMULATION_OUTCOME",
            )

        await db.flush()
        return {
            "payment_id": payment.id,
            "reservation_id": payment.reservation_id,
            "status": payment.status.value,
            "is_simulated": payment.is_simulated,
            "provider_payment_id": payment.provider_payment_id,
            "failure_reason": payment.failure_reason,
            "message": f"Simulated outcome '{outcome_upper}' executed successfully",
        }

    @classmethod
    async def get_payment(
        cls,
        db: AsyncSession,
        payment_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Payment:
        """Retrieve payment details with ownership authorization check."""
        stmt = select(Payment).where(Payment.id == payment_id)
        payment = (await db.execute(stmt)).scalar_one_or_none()
        if not payment:
            raise EntityNotFoundException(
                detail=f"Payment {payment_id} not found",
                code="PAYMENT_NOT_FOUND",
            )
        if payment.driver_id != user_id:
            raise ForbiddenException(
                detail="You do not have permission to view this payment",
                code="FORBIDDEN_PAYMENT_ACCESS",
            )
        return payment

    @classmethod
    async def cancel_payment(
        cls,
        db: AsyncSession,
        payment_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Payment:
        """Cancel a pending payment intent."""
        stmt = select(Payment).where(Payment.id == payment_id).with_for_update()
        payment = (await db.execute(stmt)).scalar_one_or_none()
        if not payment:
            raise EntityNotFoundException(
                detail=f"Payment {payment_id} not found",
                code="PAYMENT_NOT_FOUND",
            )
        if payment.driver_id != user_id:
            raise ForbiddenException(
                detail="You do not have permission to cancel this payment",
                code="FORBIDDEN_PAYMENT_ACCESS",
            )
        if payment.status in (PaymentStatusEnum.SUCCEEDED, PaymentStatusEnum.CANCELLED):
            raise ConflictException(
                detail=f"Cannot cancel payment in status {payment.status.value}",
                code="PAYMENT_CANNOT_BE_CANCELLED",
            )

        payment.status = PaymentStatusEnum.CANCELLED
        payment.failure_reason = "Cancelled by user"
        await db.flush()
        return payment
