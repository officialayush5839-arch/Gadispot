import 'package:flutter/material.dart';
import '../../../core/constants/app_constants.dart';
import '../../../core/theme/app_theme.dart';

/// Historical and upcoming parking reservations view.
class BookingsView extends StatelessWidget {
  const BookingsView({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Bookings'),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(AppTheme.spacing16),
          children: [
            _buildBookingItem(
              title: 'Brigade Pinnacle Basement Lot',
              date: 'Today, 02:00 PM - 06:00 PM',
              bay: 'BAY-B2-14',
              amount: 240,
              status: 'COMPLETED',
              statusColor: const Color(0xFF166534),
              statusBg: const Color(0xFFDCFCE7),
              isDark: isDark,
            ),
            const SizedBox(height: AppTheme.spacing12),
            _buildBookingItem(
              title: 'Forum Mall South Tower Reserved Bay',
              date: 'Yesterday, 11:00 AM - 01:30 PM',
              bay: 'BAY-G-05',
              amount: 150,
              status: 'COMPLETED',
              statusColor: const Color(0xFF166534),
              statusBg: const Color(0xFFDCFCE7),
              isDark: isDark,
            ),
            const SizedBox(height: AppTheme.spacing12),
            _buildBookingItem(
              title: 'Indiranagar Metro Stride Parking',
              date: '02 Nov 2026, 09:00 AM - 12:00 PM',
              bay: 'BAY-A-02',
              amount: 120,
              status: 'REFUNDED (GPRP)',
              statusColor: const Color(0xFF991B1B),
              statusBg: const Color(0xFFFEE2E2),
              isDark: isDark,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBookingItem({
    required String title,
    required String date,
    required String bay,
    required int amount,
    required String status,
    required Color statusColor,
    required Color statusBg,
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
                  title,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: statusBg,
                  borderRadius: BorderRadius.circular(AppTheme.radiusSm),
                ),
                child: Text(
                  status,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: statusColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            date,
            style: TextStyle(
              fontSize: 12,
              color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
            ),
          ),
          const SizedBox(height: AppTheme.spacing12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Assigned Bay: $bay',
                style: TextStyle(
                  fontSize: 12,
                  fontFamily: 'monospace',
                  color: isDark ? AppTheme.darkTextMuted : AppTheme.lightTextMuted,
                ),
              ),
              Text(
                '${AppConstants.currencySymbol}$amount',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
