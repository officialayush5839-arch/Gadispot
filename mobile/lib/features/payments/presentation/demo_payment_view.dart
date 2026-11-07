import 'package:flutter/material.dart';
import 'package:gadispot_mobile/core/theme/app_theme.dart';
import 'package:gadispot_mobile/features/payments/data/models/payment_model.dart';

/// Screen for demonstrating the dual-mode payment system in simulated mode.
/// Built strictly to anti-slop standards: monochromatic foundation, 1px borders,
/// 4px/8px grid spacing, and explicit non-monetary demo disclaimers.
class DemoPaymentView extends StatefulWidget {
  final PaymentOrder paymentOrder;
  final Future<SimulationResult> Function(String outcome, String? reason) onSimulateOutcome;
  final VoidCallback onPaymentConfirmed;

  const DemoPaymentView({
    super.key,
    required this.paymentOrder,
    required this.onSimulateOutcome,
    required this.onPaymentConfirmed,
  });

  @override
  State<DemoPaymentView> createState() => _DemoPaymentViewState();
}

class _DemoPaymentViewState extends State<DemoPaymentView> {
  bool _isLoading = false;
  String? _errorMessage;
  SimulationResult? _simulationResult;

  Future<void> _handleSimulation(String outcome, [String? reason]) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final res = await widget.onSimulateOutcome(outcome, reason);
      if (!mounted) return;
      setState(() {
        _simulationResult = res;
        _isLoading = false;
      });

      if (res.isSuccess) {
        widget.onPaymentConfirmed();
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final bgColor = isDark ? AppTheme.darkBackground : AppTheme.lightBackground;
    final surfaceColor = isDark ? AppTheme.darkSurface : AppTheme.lightSurface;
    final borderColor = isDark ? AppTheme.darkBorder : AppTheme.lightBorder;
    final textPrimary = isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary;
    final textSecondary = isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary;

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        title: const Text('Checkout & Payment'),
        backgroundColor: surfaceColor,
        elevation: 0,
        shape: Border(bottom: BorderSide(color: borderColor, width: AppTheme.borderWidth)),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppTheme.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Mandatory Hackathon Non-Monetary Demo Disclaimer
              Container(
                padding: const EdgeInsets.all(AppTheme.spacing12),
                decoration: BoxDecoration(
                  color: AppTheme.semanticWarning.withOpacity(0.08),
                  border: Border.all(color: AppTheme.semanticWarning, width: AppTheme.borderWidth),
                  borderRadius: BorderRadius.circular(AppTheme.radiusSm),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.info_outline, color: AppTheme.semanticWarning, size: 20),
                    const SizedBox(width: AppTheme.spacing12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'SIMULATED PAYMENT MODE',
                            style: theme.textTheme.labelMedium?.copyWith(
                              color: AppTheme.semanticWarning,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 0.5,
                            ),
                          ),
                          const SizedBox(height: AppTheme.spacing4),
                          Text(
                            'Demonstration environment for evaluation. No real money, payment gateway accounts, or bank cards will be debited.',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: textSecondary,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: AppTheme.spacing16),

              // Booking & Fee Summary Card
              Container(
                padding: const EdgeInsets.all(AppTheme.spacing16),
                decoration: BoxDecoration(
                  color: surfaceColor,
                  border: Border.all(color: borderColor, width: AppTheme.borderWidth),
                  borderRadius: BorderRadius.circular(AppTheme.radiusMd),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Payment Summary',
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: textPrimary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: AppTheme.spacing16),
                    _buildRow('Order Identifier', widget.paymentOrder.orderId, textSecondary, textPrimary),
                    const SizedBox(height: AppTheme.spacing8),
                    _buildRow('Reservation Ref', widget.paymentOrder.reservationId.substring(0, 8), textSecondary, textPrimary),
                    const Divider(height: AppTheme.spacing24, thickness: AppTheme.borderWidth),
                    if (widget.paymentOrder.quote != null) ...[
                      _buildRow(
                        'Base Parking Fare',
                        '₹${widget.paymentOrder.quote!.grossParkingBaseInr.toStringAsFixed(2)}',
                        textSecondary,
                        textPrimary,
                      ),
                      const SizedBox(height: AppTheme.spacing8),
                      _buildRow(
                        'Driver Convenience Fee',
                        '₹${widget.paymentOrder.quote!.convenienceFeeInr.toStringAsFixed(2)}',
                        textSecondary,
                        textPrimary,
                      ),
                      const SizedBox(height: AppTheme.spacing8),
                      _buildRow(
                        'GST Output Liability (18%)',
                        '₹${widget.paymentOrder.quote!.gstConvenienceInr.toStringAsFixed(2)}',
                        textSecondary,
                        textPrimary,
                      ),
                      const Divider(height: AppTheme.spacing24, thickness: AppTheme.borderWidth),
                    ],
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Total Payable',
                          style: theme.textTheme.titleMedium?.copyWith(
                            color: textPrimary,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          '₹${widget.paymentOrder.amountRupees.toStringAsFixed(2)}',
                          style: theme.textTheme.titleLarge?.copyWith(
                            color: textPrimary,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              const SizedBox(height: AppTheme.spacing24),

              // Simulation Execution Status Feedback
              if (_simulationResult != null) ...[
                Container(
                  padding: const EdgeInsets.all(AppTheme.spacing16),
                  decoration: BoxDecoration(
                    color: _simulationResult!.isSuccess
                        ? AppTheme.semanticSuccess.withOpacity(0.08)
                        : AppTheme.semanticError.withOpacity(0.08),
                    border: Border.all(
                      color: _simulationResult!.isSuccess ? AppTheme.semanticSuccess : AppTheme.semanticError,
                      width: AppTheme.borderWidth,
                    ),
                    borderRadius: BorderRadius.circular(AppTheme.radiusMd),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            _simulationResult!.isSuccess ? Icons.check_circle_outline : Icons.error_outline,
                            color: _simulationResult!.isSuccess ? AppTheme.semanticSuccess : AppTheme.semanticError,
                            size: 20,
                          ),
                          const SizedBox(width: AppTheme.spacing8),
                          Text(
                            _simulationResult!.isSuccess ? 'Payment Confirmed' : 'Simulation Failed',
                            style: theme.textTheme.titleSmall?.copyWith(
                              color: _simulationResult!.isSuccess ? AppTheme.semanticSuccess : AppTheme.semanticError,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppTheme.spacing8),
                      Text(
                        _simulationResult!.message,
                        style: theme.textTheme.bodyMedium?.copyWith(color: textPrimary),
                      ),
                      if (_simulationResult!.providerPaymentId != null) ...[
                        const SizedBox(height: AppTheme.spacing4),
                        Text(
                          'Simulated Transaction ID: ${_simulationResult!.providerPaymentId}',
                          style: theme.textTheme.bodySmall?.copyWith(color: textSecondary),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: AppTheme.spacing24),
              ],

              if (_errorMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(AppTheme.spacing12),
                  decoration: BoxDecoration(
                    color: AppTheme.semanticError.withOpacity(0.08),
                    border: Border.all(color: AppTheme.semanticError, width: AppTheme.borderWidth),
                    borderRadius: BorderRadius.circular(AppTheme.radiusSm),
                  ),
                  child: Text(
                    _errorMessage!,
                    style: theme.textTheme.bodySmall?.copyWith(color: AppTheme.semanticError),
                  ),
                ),
                const SizedBox(height: AppTheme.spacing16),
              ],

              // Simulation Triggers
              Text(
                'Deterministic Test Scenarios',
                style: theme.textTheme.titleSmall?.copyWith(
                  color: textSecondary,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: AppTheme.spacing12),

              // Button 1: Success
              ElevatedButton(
                onPressed: _isLoading ? null : () => _handleSimulation('SUCCESS'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.semanticSuccess,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: AppTheme.spacing16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(AppTheme.radiusSm),
                  ),
                  elevation: 0,
                ),
                child: _isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Text(
                        'Simulate Successful Payment',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
              ),

              const SizedBox(height: AppTheme.spacing12),

              // Button 2: Failure
              OutlinedButton(
                onPressed: _isLoading
                    ? null
                    : () => _handleSimulation('FAILURE', 'Simulated insufficient balance or user bank rejection'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppTheme.semanticError,
                  side: const BorderSide(color: AppTheme.semanticError, width: AppTheme.borderWidth),
                  padding: const EdgeInsets.symmetric(vertical: AppTheme.spacing16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(AppTheme.radiusSm),
                  ),
                ),
                child: const Text('Simulate Payment Failure'),
              ),

              const SizedBox(height: AppTheme.spacing12),

              // Button 3: Cancellation
              OutlinedButton(
                onPressed: _isLoading
                    ? null
                    : () => _handleSimulation('CANCEL', 'Simulated driver payment cancellation'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: textPrimary,
                  side: BorderSide(color: borderColor, width: AppTheme.borderWidth),
                  padding: const EdgeInsets.symmetric(vertical: AppTheme.spacing16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(AppTheme.radiusSm),
                  ),
                ),
                child: const Text('Simulate User Cancellation'),
              ),

              const SizedBox(height: AppTheme.spacing12),

              // Button 4: Timeout
              OutlinedButton(
                onPressed: _isLoading
                    ? null
                    : () => _handleSimulation('TIMEOUT', 'Simulated checkout window expired'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: textSecondary,
                  side: BorderSide(color: borderColor, width: AppTheme.borderWidth),
                  padding: const EdgeInsets.symmetric(vertical: AppTheme.spacing16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(AppTheme.radiusSm),
                  ),
                ),
                child: const Text('Simulate Gateway Timeout'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildRow(String label, String value, Color labelColor, Color valueColor) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: TextStyle(color: labelColor, fontSize: 13)),
        Text(value, style: TextStyle(color: valueColor, fontSize: 13, fontWeight: FontWeight.w500)),
      ],
    );
  }
}
