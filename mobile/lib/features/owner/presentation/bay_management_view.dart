import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

/// Space Owner Bay Management with physical dimensions and schedules.
class BayManagementView extends StatelessWidget {
  const BayManagementView({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Parking Bays & Schedules'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () {},
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(AppTheme.spacing16),
          children: [
            _buildBayItem(
              identifier: 'BAY-01 (Driveway East)',
              dimensions: '5,000mm L × 2,400mm W × 2,200mm H',
              schedule: 'Mon–Sun, 08:00 AM – 10:00 PM',
              status: 'AVAILABLE',
              rate: '₹50/hr',
              isDark: isDark,
            ),
            const SizedBox(height: AppTheme.spacing12),
            _buildBayItem(
              identifier: 'BAY-02 (Covered Garage)',
              dimensions: '5,500mm L × 2,600mm W × 2,400mm H',
              schedule: 'Mon–Fri, 09:00 AM – 06:00 PM',
              status: 'OCCUPIED (KA01MJ4092)',
              rate: '₹60/hr',
              isDark: isDark,
            ),
            const SizedBox(height: AppTheme.spacing12),
            _buildBayItem(
              identifier: 'BAY-03 (EV Charger Slot)',
              dimensions: '5,000mm L × 2,500mm W × 2,200mm H',
              schedule: '24/7 Unlimited Access',
              status: 'AVAILABLE',
              rate: '₹75/hr',
              isDark: isDark,
            ),
            const SizedBox(height: AppTheme.spacing12),
            _buildBayItem(
              identifier: 'BAY-04 (Paved Porch)',
              dimensions: '4,800mm L × 2,300mm W × 2,100mm H',
              schedule: 'Blackout Scheduled: Family Visiting',
              status: 'MANUAL BLACKOUT',
              rate: '₹40/hr',
              isDark: isDark,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBayItem({
    required String identifier,
    required String dimensions,
    required String schedule,
    required String status,
    required String rate,
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
              Text(
                identifier,
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
                ),
              ),
              Text(
                rate,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppTheme.spacing8),
          Text(
            'Physical Clearance: $dimensions',
            style: TextStyle(
              fontSize: 12,
              fontFamily: 'monospace',
              color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Schedule: $schedule',
            style: TextStyle(
              fontSize: 12,
              color: isDark ? AppTheme.darkTextMuted : AppTheme.lightTextMuted,
            ),
          ),
          const SizedBox(height: AppTheme.spacing12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: isDark ? AppTheme.darkSurfaceElevated : AppTheme.lightSurfaceElevated,
              borderRadius: BorderRadius.circular(AppTheme.radiusSm),
              border: Border.all(
                color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
                width: AppTheme.borderWidth,
              ),
            ),
            child: Text(
              status,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
