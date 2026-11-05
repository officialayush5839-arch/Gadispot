import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

/// Operations property authorization and deed review queue.
class ApprovalsView extends StatelessWidget {
  const ApprovalsView({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Property Approvals Queue'),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(AppTheme.spacing16),
          children: [
            _buildApprovalCard(
              propertyName: 'Brigade Gateway B3 Bay Listing',
              owner: 'Suresh Kumar (+91 9845012345)',
              address: 'Dr Rajkumar Rd, Rajajinagar, Bengaluru',
              baysCount: 4,
              docs: 'Electricity Bill + Society NOC Uploaded',
              isDark: isDark,
            ),
            const SizedBox(height: AppTheme.spacing12),
            _buildApprovalCard(
              propertyName: 'Indiranagar 100ft Road Gated Lot',
              owner: 'Ananya Sharma (+91 9900198765)',
              address: '12th Main Road, HAL 2nd Stage, Indiranagar',
              baysCount: 2,
              docs: 'Sale Deed + Property Tax Receipt Uploaded',
              isDark: isDark,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildApprovalCard({
    required String propertyName,
    required String owner,
    required String address,
    required int baysCount,
    required String docs,
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
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  propertyName,
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFFFEF3C7),
                  borderRadius: BorderRadius.circular(AppTheme.radiusSm),
                ),
                child: const Text(
                  'PENDING REVIEW',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF92400E),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            'Owner: $owner',
            style: TextStyle(
              fontSize: 12,
              color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            address,
            style: TextStyle(
              fontSize: 12,
              color: isDark ? AppTheme.darkTextMuted : AppTheme.lightTextMuted,
            ),
          ),
          const SizedBox(height: AppTheme.spacing12),
          Text(
            'Verification Evidence: $docs ($baysCount parking bays)',
            style: TextStyle(
              fontSize: 11,
              fontFamily: 'monospace',
              color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
            ),
          ),
          const SizedBox(height: AppTheme.spacing16),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.semanticError,
                    side: const BorderSide(color: AppTheme.semanticError),
                  ),
                  onPressed: () {},
                  child: const Text('REJECT'),
                ),
              ),
              const SizedBox(width: AppTheme.spacing12),
              Expanded(
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.semanticSuccess,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: () {},
                  child: const Text('APPROVE & PUBLISH'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
