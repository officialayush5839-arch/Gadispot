import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gadispot_mobile/core/theme/app_theme.dart';
import 'package:gadispot_mobile/features/payments/data/models/payment_model.dart';
import 'package:gadispot_mobile/features/payments/presentation/demo_payment_view.dart';

void main() {
  final sampleOrder = PaymentOrder(
    paymentId: 'pay_test_uuid_123',
    reservationId: 'res_test_uuid_456',
    orderId: 'order_sim_789',
    amountPaise: 12500,
    currency: 'INR',
    status: 'CREATED',
    gateway: 'demo',
    isSimulated: true,
    quote: const PaymentQuote(
      grossParkingBaseInr: 100.0,
      convenienceFeeInr: 10.0,
      gstConvenienceInr: 1.80,
      totalDriverPaidInr: 111.80,
      platformCommissionInr: 15.0,
      gstCommissionInr: 2.70,
      ownerNetEntitlementInr: 82.30,
      totalDriverPaidPaise: 11180,
    ),
  );

  testWidgets('DemoPaymentView displays mandatory non-monetary disclaimer', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.darkTheme,
        home: DemoPaymentView(
          paymentOrder: sampleOrder,
          onSimulateOutcome: (String outcome, String? reason) async => SimulationResult(
            paymentId: sampleOrder.paymentId,
            reservationId: sampleOrder.reservationId,
            status: 'SUCCEEDED',
            isSimulated: true,
            message: 'Success',
          ),
          onPaymentConfirmed: () {},
        ),
      ),
    );

    // Verify presence of non-monetary demo disclaimer
    expect(find.text('SIMULATED PAYMENT MODE'), findsOneWidget);
    expect(
      find.textContaining('No real money, payment gateway accounts, or bank cards will be debited.'),
      findsOneWidget,
    );

    // Verify fare summary
    expect(find.text('Payment Summary'), findsOneWidget);
    expect(find.text('₹125.00'), findsOneWidget);

    // Verify scenario buttons
    expect(find.text('Simulate Successful Payment'), findsOneWidget);
    expect(find.text('Simulate Payment Failure'), findsOneWidget);
    expect(find.text('Simulate User Cancellation'), findsOneWidget);
    expect(find.text('Simulate Gateway Timeout'), findsOneWidget);
  });

  testWidgets('Triggering simulate success invokes callback and displays confirmation', (WidgetTester tester) async {
    String? capturedOutcome;
    bool confirmedTriggered = false;

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.darkTheme,
        home: DemoPaymentView(
          paymentOrder: sampleOrder,
          onSimulateOutcome: (String outcome, String? reason) async {
            capturedOutcome = outcome;
            return SimulationResult(
              paymentId: sampleOrder.paymentId,
              reservationId: sampleOrder.reservationId,
              status: 'SUCCEEDED',
              isSimulated: true,
              providerPaymentId: 'pay_sim_success_999',
              message: 'Simulated payment succeeded',
            );
          },
          onPaymentConfirmed: () {
            confirmedTriggered = true;
          },
        ),
      ),
    );

    await tester.tap(find.text('Simulate Successful Payment'));
    await tester.pumpAndSettle();

    expect(capturedOutcome, equals('SUCCESS'));
    expect(confirmedTriggered, isTrue);
    expect(find.text('Payment Confirmed'), findsOneWidget);
    expect(find.text('Simulated payment succeeded'), findsOneWidget);
  });
}
