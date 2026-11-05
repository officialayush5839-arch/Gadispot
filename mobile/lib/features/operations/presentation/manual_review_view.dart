import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

/// Operations manual review queue for dispute resolution and manual payout overrides.
class ManualReviewView extends StatelessWidget {
  const ManualReviewView({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Manual Overrides & Disputes'),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(AppTheme.spacing16),
          children: [
            _buildReviewItem(
              title: 'Disputed Overstay Penalty (KA01MJ4092)',
              description: 'Driver reported barrier gate failure at exit; billed 1.5x tariff (₹180).',
              timestamp: 'Reported 45m ago',
              actionLabel: 'WAIVE & REFUND PENALTY',
              isDark: isDark,
            ),
            const SizedBox(height: AppTheme.spacing12),
            _buildReviewItem(
              title: 'Late Payment Resolution Protocol (LPRP Race Lost)',
              description: 'Hold expired during UPI processing; space booked by another driver. Auto-refund pending UTR generation.',
              timestamp: 'Reported 2h ago',
              actionLabel: 'FORCE GATEWAY REFUND RECONCILIATION',
              isDark: isDark,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildReviewItem({
    required String title,
    required String description,
    required String timestamp,
    required String actionLabel,
    required bool isDark,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppTheme.spacing16),
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
            title,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            description,
            style: TextStyle(
              fontSize: 12,
              color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
              height: 1.4,
            ),
          ),
          const SizedBox(height: AppTheme.spacing8),
          Text(
            timestamp,
            style: TextStyle(
              fontSize: 11,
              fontFamily: 'monospace',
              color: isDark ? AppTheme.darkTextMuted : AppTheme.lightTextMuted,
            ),
          ),
          const SizedBox(height: AppTheme.spacing12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () {},
              child: Text(actionLabel),
            ),
          ),
        ],
      ),
    );
  }
}
