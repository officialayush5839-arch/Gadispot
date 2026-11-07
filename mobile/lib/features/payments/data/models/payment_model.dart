/// Domain models for Payment quotes, initiation intents, and demo simulation results.

class PaymentQuote {
  final double grossParkingBaseInr;
  final double convenienceFeeInr;
  final double gstConvenienceInr;
  final double totalDriverPaidInr;
  final double platformCommissionInr;
  final double gstCommissionInr;
  final double ownerNetEntitlementInr;
  final int totalDriverPaidPaise;

  const PaymentQuote({
    required this.grossParkingBaseInr,
    required this.convenienceFeeInr,
    required this.gstConvenienceInr,
    required this.totalDriverPaidInr,
    required this.platformCommissionInr,
    required this.gstCommissionInr,
    required this.ownerNetEntitlementInr,
    required this.totalDriverPaidPaise,
  });

  factory PaymentQuote.fromJson(Map<String, dynamic> json) {
    final paise = json['paise'] as Map<String, dynamic>? ?? {};
    return PaymentQuote(
      grossParkingBaseInr: (json['gross_parking_base_inr'] as num?)?.toDouble() ?? 0.0,
      convenienceFeeInr: (json['convenience_fee_inr'] as num?)?.toDouble() ?? 0.0,
      gstConvenienceInr: (json['gst_convenience_inr'] as num?)?.toDouble() ?? 0.0,
      totalDriverPaidInr: (json['total_driver_paid_inr'] as num?)?.toDouble() ?? 0.0,
      platformCommissionInr: (json['platform_commission_inr'] as num?)?.toDouble() ?? 0.0,
      gstCommissionInr: (json['gst_commission_inr'] as num?)?.toDouble() ?? 0.0,
      ownerNetEntitlementInr: (json['owner_net_entitlement_inr'] as num?)?.toDouble() ?? 0.0,
      totalDriverPaidPaise: (paise['total_driver_paid'] as num?)?.toInt() ?? 0,
    );
  }
}

class PaymentOrder {
  final String paymentId;
  final String reservationId;
  final String orderId;
  final int amountPaise;
  final String currency;
  final String status;
  final String gateway;
  final bool isSimulated;
  final bool isExperimental;
  final PaymentQuote? quote;

  const PaymentOrder({
    required this.paymentId,
    required this.reservationId,
    required this.orderId,
    required this.amountPaise,
    required this.currency,
    required this.status,
    required this.gateway,
    required this.isSimulated,
    this.isExperimental = false,
    this.quote,
  });

  double get amountRupees => amountPaise / 100.0;

  factory PaymentOrder.fromJson(Map<String, dynamic> json) {
    return PaymentOrder(
      paymentId: json['payment_id'] as String? ?? '',
      reservationId: json['reservation_id'] as String? ?? '',
      orderId: json['order_id'] as String? ?? '',
      amountPaise: (json['amount_paise'] as num?)?.toInt() ?? 0,
      currency: json['currency'] as String? ?? 'INR',
      status: json['status'] as String? ?? 'CREATED',
      gateway: json['gateway'] as String? ?? 'demo',
      isSimulated: json['is_simulated'] as bool? ?? true,
      isExperimental: json['is_experimental'] as bool? ?? false,
      quote: json['quote'] != null ? PaymentQuote.fromJson(json['quote'] as Map<String, dynamic>) : null,
    );
  }
}

class SimulationResult {
  final String paymentId;
  final String reservationId;
  final String status;
  final bool isSimulated;
  final String? providerPaymentId;
  final String? failureReason;
  final String message;

  const SimulationResult({
    required this.paymentId,
    required this.reservationId,
    required this.status,
    required this.isSimulated,
    this.providerPaymentId,
    this.failureReason,
    required this.message,
  });

  bool get isSuccess => status.toUpperCase() == 'SUCCEEDED';

  factory SimulationResult.fromJson(Map<String, dynamic> json) {
    return SimulationResult(
      paymentId: json['payment_id'] as String? ?? '',
      reservationId: json['reservation_id'] as String? ?? '',
      status: json['status'] as String? ?? '',
      isSimulated: json['is_simulated'] as bool? ?? true,
      providerPaymentId: json['provider_payment_id'] as String?,
      failureReason: json['failure_reason'] as String?,
      message: json['message'] as String? ?? '',
    );
  }
}
