import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/offline_banner.dart';
import '../../../core/widgets/qr_container.dart';

/// Active Parking Pass and Reservation Tracking View.
class ActiveReservationView extends StatefulWidget {
  const ActiveReservationView({super.key});

  @override
  State<ActiveReservationView> createState() => _ActiveReservationViewState();
}

class _ActiveReservationViewState extends State<ActiveReservationView> {
  bool _isSubterraneanOffline = false;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Digital Parking Pass'),
        actions: [
          IconButton(
            icon: Icon(
              _isSubterraneanOffline ? Icons.signal_cellular_connected_no_internet_4_bar : Icons.signal_cellular_alt,
              color: _isSubterraneanOffline ? AppTheme.semanticWarning : null,
            ),
            tooltip: 'Toggle Offline Simulation',
            onPressed: () {
              setState(() => _isSubterraneanOffline = !_isSubterraneanOffline);
            },
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Subterranean dead-zone banner
            OfflineBanner(
              isOffline: _isSubterraneanOffline,
              customMessage: 'Subterranean Basement B2 (No Cell Signal) — Offline Pass Cached & Active.',
              onRetry: () {
                setState(() => _isSubterraneanOffline = false);
              },
            ),

            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(AppTheme.spacing16),
                child: Column(
                  children: [
                    // High-contrast QR Container
                    const QrContainer(
                      passToken: 'spx_ent_8f9a2b4c1e0d3f7a6b5c4d3e2f1a0b9c',
                      spaceIdentifier: 'BAY-B2-14',
                      vehiclePlate: 'KA01MJ4092',
                      timeRemainingText: '03h 42m remaining',
                      size: 200,
                    ),
                    const SizedBox(height: AppTheme.spacing20),

                    // Location & Reservation Details Container
                    Container(
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
                                'SESSION STATUS',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                  color: isDark ? AppTheme.darkTextMuted : AppTheme.lightTextMuted,
                                  letterSpacing: 0.5,
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: AppTheme.spacing8,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFDCFCE7),
                                  borderRadius: BorderRadius.circular(AppTheme.radiusSm),
                                ),
                                child: const Text(
                                  'ACTIVE IN-SESSION',
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.w700,
                                    color: Color(0xFF166534),
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: AppTheme.spacing12),
                          Text(
                            'Brigade Pinnacle Basement Lot',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                              color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Level -2, Pillar C-12, Koramangala 4th Block',
                            style: TextStyle(
                              fontSize: 13,
                              color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
                            ),
                          ),
                          const Divider(height: AppTheme.spacing24),
                          _buildDetailRow('Start Time', 'Today, 02:00 PM', isDark),
                          const SizedBox(height: AppTheme.spacing8),
                          _buildDetailRow('End Time', 'Today, 06:00 PM', isDark),
                          const SizedBox(height: AppTheme.spacing8),
                          _buildDetailRow('Booked Vehicle', 'KA01MJ4092 (Hyundai Creta)', isDark),
                          const SizedBox(height: AppTheme.spacing8),
                          _buildDetailRow('Tariff', '₹60/hr (Pre-paid ₹240)', isDark),
                        ],
                      ),
                    ),
                    const SizedBox(height: AppTheme.spacing16),

                    // Actions: Extend Duration & Get Directions
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            icon: const Icon(Icons.navigation_outlined, size: 16),
                            label: const Text('DIRECTIONS'),
                            onPressed: () {},
                          ),
                        ),
                        const SizedBox(width: AppTheme.spacing12),
                        Expanded(
                          child: ElevatedButton.icon(
                            icon: const Icon(Icons.more_time, size: 16),
                            label: const Text('EXTEND TIME'),
                            onPressed: () {},
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value, bool isDark) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
          ),
        ),
        Text(
          value,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
          ),
        ),
      ],
    );
  }
}
