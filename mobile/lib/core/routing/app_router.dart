import 'package:flutter/material.dart';
import '../../features/auth/presentation/login_view.dart';
import '../../features/auth/presentation/otp_view.dart';
import '../../features/driver/presentation/driver_shell.dart';
import '../../features/owner/presentation/owner_shell.dart';
import '../../features/guard/presentation/guard_shell.dart';
import '../../features/operations/presentation/ops_shell.dart';

/// User roles in the Gadispot marketplace matching backend claims.
enum UserRole {
  driver,
  owner,
  guard,
  operations,
}

extension UserRoleExtension on UserRole {
  String get roleName {
    switch (this) {
      case UserRole.driver:
        return 'DRIVER';
      case UserRole.owner:
        return 'SPACE_OWNER';
      case UserRole.guard:
        return 'SECURITY_GUARD';
      case UserRole.operations:
        return 'OPERATIONS';
    }
  }

  static UserRole? fromString(String? role) {
    if (role == null) return null;
    final normalized = role.trim().toUpperCase();
    switch (normalized) {
      case 'DRIVER':
        return UserRole.driver;
      case 'SPACE_OWNER':
      case 'OWNER':
        return UserRole.owner;
      case 'SECURITY_GUARD':
      case 'GUARD':
        return UserRole.guard;
      case 'OPERATIONS':
      case 'OPS':
      case 'ADMIN':
        return UserRole.operations;
      default:
        return null;
    }
  }
}

/// Dynamic Role-Based App Router for Gadispot Mobile Application.
class AppRouter {
  AppRouter._();

  // Route paths
  static const String root = '/';
  static const String login = '/login';
  static const String otp = '/otp';
  static const String driver = '/driver';
  static const String driverSearch = '/driver/search';
  static const String driverReservations = '/driver/reservations';
  static const String driverBookings = '/driver/bookings';
  static const String driverVehicles = '/driver/vehicles';

  static const String owner = '/owner';
  static const String ownerOverview = '/owner/overview';
  static const String ownerBays = '/owner/bays';
  static const String ownerEarnings = '/owner/earnings';

  static const String guard = '/guard';
  static const String guardScanner = '/guard/scanner';
  static const String guardLogs = '/guard/logs';

  static const String ops = '/ops';
  static const String opsApprovals = '/ops/approvals';
  static const String opsReviews = '/ops/reviews';

  static const String unauthorized = '/unauthorized';

  /// Resolves the home navigation shell based on the active authenticated user role.
  static String resolveInitialRoute(UserRole? role) {
    if (role == null) {
      return login;
    }
    switch (role) {
      case UserRole.driver:
        return driver;
      case UserRole.owner:
        return owner;
      case UserRole.guard:
        return guard;
      case UserRole.operations:
        return ops;
    }
  }

  /// Security guard ensuring users cannot navigate to unauthorized role shells.
  static bool isRouteAuthorizedForRole(String route, UserRole? role) {
    if (route == login || route == otp || route == root) {
      return true;
    }
    if (role == null) {
      return false;
    }
    if (route.startsWith('/driver')) {
      return role == UserRole.driver;
    }
    if (route.startsWith('/owner')) {
      return role == UserRole.owner;
    }
    if (route.startsWith('/guard')) {
      return role == UserRole.guard;
    }
    if (route.startsWith('/ops')) {
      return role == UserRole.operations;
    }
    return true;
  }

  /// Route generator
  static Route<dynamic> onGenerateRoute(RouteSettings settings) {
    switch (settings.name) {
      case root:
      case login:
        return MaterialPageRoute(builder: (_) => const LoginView());

      case otp:
        final phone = settings.arguments as String? ?? '';
        return MaterialPageRoute(builder: (_) => OtpView(phoneNumber: phone));

      case driver:
      case driverSearch:
      case driverReservations:
      case driverBookings:
      case driverVehicles:
        return MaterialPageRoute(builder: (_) => const DriverShell());

      case owner:
      case ownerOverview:
      case ownerBays:
      case ownerEarnings:
        return MaterialPageRoute(builder: (_) => const OwnerShell());

      case guard:
      case guardScanner:
      case guardLogs:
        return MaterialPageRoute(builder: (_) => const GuardShell());

      case ops:
      case opsApprovals:
      case opsReviews:
        return MaterialPageRoute(builder: (_) => const OpsShell());

      case unauthorized:
        return MaterialPageRoute(
          builder: (_) => Scaffold(
            appBar: AppBar(title: const Text('Access Denied')),
            body: const Center(
              child: Text(
                'You do not have permission to view this role module.',
                style: TextStyle(fontSize: 16),
              ),
            ),
          ),
        );

      default:
        return MaterialPageRoute(
          builder: (_) => Scaffold(
            appBar: AppBar(title: const Text('Route Not Found')),
            body: Center(
              child: Text('No route defined for ${settings.name}'),
            ),
          ),
        );
    }
  }
}
