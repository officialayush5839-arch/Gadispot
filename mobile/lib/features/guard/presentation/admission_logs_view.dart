import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

/// Gate admission history and scan audit log.
class AdmissionLogsView extends StatelessWidget {
  const AdmissionLogsView({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Shift Admission Logs'),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(AppTheme.spacing16),
          children: [
            _buildLogItem(
              time: '02:04 PM',
              plate: 'KA01MJ4092',
              bay: 'BAY-B2-14',
              type: 'ENTRY SCAN (PASS BURNED)',
              isSuccess: true,
              isDark: isDark,
            ),
            const SizedBox(height: AppTheme.spacing8),
            _buildLogItem(
              time: '01:52 PM',
              plate: 'KA03HA2201',
              bay: 'BAY-B1-02',
              type: 'EXIT SCAN (COMPLETED)',
              isSuccess: true,
              isDark: isDark,
            ),
            const SizedBox(height: AppTheme.spacing8),
            _buildLogItem(
              time: '01:15 PM',
              plate: 'KA05D9981',
              bay: 'UNASSIGNED',
              type: 'REPLAY BLOCKED (ALREADY CONSUMED)',
              isSuccess: false,
              isDark: isDark,
            ),
            const SizedBox(height: AppTheme.spacing8),
            _buildLogItem(
              time: '12:40 PM',
              plate: 'KA04MM1020',
              bay: 'BAY-B2-08',
              type: 'OFFLINE MANUAL PHOTO ADMISSION',
              isSuccess: true,
              isDark: isDark,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLogItem({
    required String time,
    required String plate,
    required String bay,
    required String type,
    required bool isSuccess,
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
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: isSuccess ? AppTheme.semanticSuccess : AppTheme.semanticError,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              const SizedBox(width: AppTheme.spacing12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '$plate • $bay',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    type,
                    style: TextStyle(
                      fontSize: 11,
                      color: isDark ? AppTheme.darkTextMuted : AppTheme.lightTextMuted,
                    ),
                  ),
                ],
              ),
            ],
          ),
          Text(
            time,
            style: TextStyle(
              fontSize: 12,
              fontFamily: 'monospace',
              color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
            ),
          ),
        ],
      ),
    );
  }
}
