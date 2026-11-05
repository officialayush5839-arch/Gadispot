import 'package:flutter/material.dart';
import '../../../core/constants/app_constants.dart';
import '../../../core/theme/app_theme.dart';

/// Driver Proximity Spatial Search View.
class SearchView extends StatefulWidget {
  const SearchView({super.key});

  @override
  State<SearchView> createState() => _SearchViewState();
}

class _SearchViewState extends State<SearchView> {
  final _searchController = TextEditingController(text: 'Koramangala 4th Block, Bengaluru');
  double _radiusKm = 3.0;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Find Guaranteed Parking'),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: () {},
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Search Input Header
            Container(
              padding: const EdgeInsets.all(AppTheme.spacing16),
              decoration: BoxDecoration(
                color: isDark ? AppTheme.darkSurface : AppTheme.lightSurface,
                border: Border(
                  bottom: BorderSide(
                    color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
                    width: AppTheme.borderWidth,
                  ),
                ),
              ),
              child: Column(
                children: [
                  TextField(
                    controller: _searchController,
                    decoration: InputDecoration(
                      hintText: 'Enter destination or landmark',
                      prefixIcon: const Icon(Icons.location_on_outlined, size: 20),
                      suffixIcon: IconButton(
                        icon: const Icon(Icons.my_location, size: 20),
                        onPressed: () {},
                      ),
                    ),
                  ),
                  const SizedBox(height: AppTheme.spacing12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Search Radius: ${_radiusKm.toStringAsFixed(1)} km',
                        style: TextStyle(
                          fontSize: 12,
                          color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
                        ),
                      ),
                      Text(
                        'Max 5.0 km',
                        style: TextStyle(
                          fontSize: 12,
                          color: isDark ? AppTheme.darkTextMuted : AppTheme.lightTextMuted,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Search Results List
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(AppTheme.spacing16),
                children: [
                  _buildParkingSpaceCard(
                    title: 'Brigade Pinnacle Basement Parking',
                    address: '80ft Road, Koramangala 4th Block',
                    distanceKm: 0.4,
                    availableBays: 3,
                    ratePerHour: 60,
                    evCharging: true,
                    isDark: isDark,
                  ),
                  const SizedBox(height: AppTheme.spacing12),
                  _buildParkingSpaceCard(
                    title: 'Prestige Meridian Covered Bay',
                    address: '100ft Inner Ring Road',
                    distanceKm: 1.1,
                    availableBays: 1,
                    ratePerHour: 50,
                    evCharging: false,
                    isDark: isDark,
                  ),
                  const SizedBox(height: AppTheme.spacing12),
                  _buildParkingSpaceCard(
                    title: 'Green Glen Gated Residential Driveway',
                    address: 'Bellandur Main Road',
                    distanceKm: 2.8,
                    availableBays: 2,
                    ratePerHour: 40,
                    evCharging: false,
                    isDark: isDark,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildParkingSpaceCard({
    required String title,
    required String address,
    required double distanceKm,
    required int availableBays,
    required int ratePerHour,
    required bool evCharging,
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
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
                    letterSpacing: -0.2,
                  ),
                ),
              ),
              Text(
                '${AppConstants.currencySymbol}$ratePerHour/hr',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppTheme.spacing4),
          Text(
            address,
            style: TextStyle(
              fontSize: 12,
              color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
            ),
          ),
          const SizedBox(height: AppTheme.spacing12),
          Row(
            children: [
              _buildTag('${distanceKm.toStringAsFixed(1)} km away', isDark),
              const SizedBox(width: AppTheme.spacing8),
              _buildTag('$availableBays bays free', isDark),
              if (evCharging) ...[
                const SizedBox(width: AppTheme.spacing8),
                _buildTag('EV Fast Charging', isDark),
              ],
            ],
          ),
          const SizedBox(height: AppTheme.spacing16),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () {},
                  child: const Text('VIEW DETAILS'),
                ),
              ),
              const SizedBox(width: AppTheme.spacing12),
              Expanded(
                child: ElevatedButton(
                  onPressed: () {},
                  child: const Text('HOLD BAY (480s)'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTag(String text, bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppTheme.spacing8,
        vertical: AppTheme.spacing4,
      ),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkSurfaceElevated : AppTheme.lightSurfaceElevated,
        borderRadius: BorderRadius.circular(AppTheme.radiusSm),
        border: Border.all(
          color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
          width: AppTheme.borderWidth,
        ),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w500,
          color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
        ),
      ),
    );
  }
}
