/// Centralized API endpoint routes conforming to PRD V2.3.2 and FastAPI backend routes.

class ApiEndpoints {
  ApiEndpoints._();

  static const String apiVersion = '/api/v1';

  // Health and probe routes
  static const String healthLive = '/health/live';
  static const String healthReady = '/health/ready';
  static const String healthApi = '$apiVersion/health';

  // Authentication & Session
  static const String authFirebaseExchange = '$apiVersion/auth/firebase-exchange';
  static const String authRefresh = '$apiVersion/auth/refresh';
  static const String authLogout = '$apiVersion/auth/logout';
  static const String authProfile = '$apiVersion/auth/me';

  // Bookings & Reservations
  static const String bookingsHold = '$apiVersion/bookings/hold';
  static const String bookingsConfirm = '$apiVersion/bookings/confirm';
  static const String bookingsActive = '$apiVersion/bookings/active';
  static const String bookingsHistory = '$apiVersion/bookings/history';
  static String bookingDetail(String id) => '$apiVersion/bookings/$id';
  static String bookingExtend(String id) => '$apiVersion/bookings/$id/extend';
  static String bookingCancel(String id) => '$apiVersion/bookings/$id/cancel';

  // Driver Features
  static const String searchProximity = '$apiVersion/search/proximity';
  static const String vehicles = '$apiVersion/vehicles';
  static String vehicleDetail(String id) => '$apiVersion/vehicles/$id';

  // Space Owner Features
  static const String properties = '$apiVersion/properties';
  static String propertyDetail(String id) => '$apiVersion/properties/$id';
  static String propertySpaces(String propertyId) => '$apiVersion/properties/$propertyId/spaces';
  static String propertySchedules(String propertyId) => '$apiVersion/properties/$propertyId/schedules';
  static const String ownerEarnings = '$apiVersion/owner/earnings';

  // Guard & Access Control
  static const String accessValidateScan = '$apiVersion/access/validate-scan';
  static const String accessShiftSchedule = '$apiVersion/access/shift-schedule';
  static const String accessManualAdmission = '$apiVersion/access/manual-admission';
  static const String accessScanLogs = '$apiVersion/access/logs';

  // Payments & Checkout
  static const String payments = '$apiVersion/payments';
  static const String paymentProviders = '$apiVersion/payments/providers';
  static String paymentDetail(String id) => '$apiVersion/payments/$id';
  static String paymentDemoComplete(String id) => '$apiVersion/payments/$id/demo/complete';
  static String paymentCancel(String id) => '$apiVersion/payments/$id/cancel';
  static const String paymentSimulatePayout = '$apiVersion/payments/payouts/simulate';

  // Operations / Admin
  static const String adminPropertyQueue = '$apiVersion/admin/properties/queue';
  static String adminApproveProperty(String id) => '$apiVersion/admin/properties/$id/approve';
  static String adminRejectProperty(String id) => '$apiVersion/admin/properties/$id/reject';
  static const String adminLedgerReconcile = '$apiVersion/admin/ledger/reconcile';
}
