import 'package:flutter/material.dart';
import '../../../core/constants/app_constants.dart';
import '../../../core/theme/app_theme.dart';

/// Space Owner Earnings & Host Payouts Ledger View.
class EarningsView extends StatelessWidget {
  const EarningsView({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Host Earnings & Payouts'),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(AppTheme.spacing16),
          children: [
            // Available Balance Card
            Container(
              padding: const EdgeInsets.all(AppTheme.spacing20),
              decoration: BoxDecoration(
                color: isDark ? AppTheme.darkSurface : AppTheme.lightSurface,
                borderRadius: BorderRadius.circular(AppTheme.radiusMd),
                border: Border.all(
                  color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
                  width: AppTheme.borderWidth,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'SETTLED HOST BALANCE',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.5,
                      color: isDark ? AppTheme.darkTextMuted : AppTheme.lightTextMuted,
                    ),
                  ),
                  const SizedBox(height: AppTheme.spacing8),
                  Text(
                    '${AppConstants.currencySymbol}14,680.00',
                    style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.w800,
                      color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: AppTheme.spacing8),
                  Text(
                    'Weekly automated batch bank payout scheduled for Tuesday, 10 Nov 2026.',
                    style: TextStyle(
                      fontSize: 12,
                      color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppTheme.spacing20),

            Text(
              'PAYOUT HISTORY & GENERAL LEDGER',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.5,
                color: isDark ? AppTheme.darkTextMuted : AppTheme.lightTextMuted,
              ),
            ),
            const SizedBox(height: AppTheme.spacing12),

            _buildLedgerEntry(
              date: '03 Nov 2026',
              desc: 'Weekly Direct Bank Settlement (RazorpayX UTR: RZX89421)',
              amount: '₹12,400.00',
              status: 'SETTLED',
              isDebit: true,
              isDark: isDark,
            ),
            const SizedBox(height: AppTheme.spacing8),
            _buildLedgerEntry(
              date: '03 Nov 2026',
              desc: 'Parking Session Revenue (KA01MJ4092)',
              amount: '+₹240.00',
              status: 'POSTED',
              isDebit: false,
              isDark: isDark,
            ),
            const SizedBox(height: AppTheme.spacing8),
            _buildLedgerEntry(
              date: '02 Nov 2026',
              desc: 'Parking Session Revenue (KA03AB9901)',
              amount: '+₹180.00',
              status: 'POSTED',
              isDebit: false,
              isDark: isDark,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLedgerEntry({
    required String date,
    required String desc,
    required String amount,
    required String status,
    required bool isDebit,
    required bool isDark,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppTheme.spacing12),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkSurface : AppTheme.lightSurface,
        borderRadius: BorderRadius.circular(AppTheme.radiusSm),
        border: Border.all(
          color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
          width: AppTheme.borderWidth,
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  desc,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '$date • $status',
                  style: TextStyle(
                    fontSize: 11,
                    color: isDark ? AppTheme.darkTextMuted : AppTheme.lightTextMuted,
                  ),
                ),
              ],
            ),
          ),
          Text(
            amount,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: isDebit
                  ? (isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary)
                  : AppTheme.semanticSuccess,
            ),
          ),
        ],
      ),
    );
  }
}
