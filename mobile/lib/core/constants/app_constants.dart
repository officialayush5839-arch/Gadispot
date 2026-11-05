/// Authoritative application constants derived from PRD V2.3.2.

class AppConstants {
  AppConstants._();

  static const String appName = 'Gadispot';
  static const String appTagline = 'Guaranteed Urban Parking Marketplace';

  // Authoritative Hold Policy (POL-HLD-01)
  static const int holdDurationSeconds = 480; // 8 minutes
  static const int holdWarningAlertSeconds = 360; // 6 minutes warning
  static const int arrivalNotificationLeadSeconds = 900; // 15 minutes before slot start

  // Currency & Locale
  static const String currencyCode = 'INR';
  static const String currencySymbol = '₹';
  static const String defaultLocale = 'en_IN';

  // Search Defaults
  static const double defaultSearchRadiusMeters = 3000.0; // 3 km default
  static const double maxSearchRadiusMeters = 5000.0; // 5 km maximum
  static const int defaultSearchLimit = 20;

  // Indian Vehicle Plate Regex: 2 letters state + 2 digits district + 1-2 letters series + 4 digits
  static final RegExp indianPlateRegex = RegExp(
    r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$',
    caseSensitive: true,
  );

  // Clearance margins (Vehicle-Bay compatibility in meters)
  static const double clearanceLengthMarginMeters = 0.3;
  static const double clearanceWidthMarginMeters = 0.4;
  static const double clearanceHeightMarginMeters = 0.1;

  // Gate photo retention limit under DPDPA (Days)
  static const int gatePhotoRetentionDays = 7;
}
