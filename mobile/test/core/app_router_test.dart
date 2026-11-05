import 'package:flutter_test/flutter_test.dart';
import 'package:gadispot_mobile/core/routing/app_router.dart';

void main() {
  group('AppRouter Role-Based Routing Tests', () {
    test('resolveInitialRoute maps UserRole correctly to designated shells', () {
      expect(AppRouter.resolveInitialRoute(null), equals(AppRouter.login));
      expect(AppRouter.resolveInitialRoute(UserRole.driver), equals(AppRouter.driver));
      expect(AppRouter.resolveInitialRoute(UserRole.owner), equals(AppRouter.owner));
      expect(AppRouter.resolveInitialRoute(UserRole.guard), equals(AppRouter.guard));
      expect(AppRouter.resolveInitialRoute(UserRole.operations), equals(AppRouter.ops));
    });

    test('isRouteAuthorizedForRole protects driver shell from unauthorized roles', () {
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.driver, UserRole.driver), isTrue);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.driverSearch, UserRole.driver), isTrue);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.driver, UserRole.guard), isFalse);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.driver, UserRole.owner), isFalse);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.driver, null), isFalse);
    });

    test('isRouteAuthorizedForRole protects guard shell from unauthorized roles', () {
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.guard, UserRole.guard), isTrue);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.guardScanner, UserRole.guard), isTrue);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.guard, UserRole.driver), isFalse);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.guard, UserRole.owner), isFalse);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.guard, null), isFalse);
    });

    test('isRouteAuthorizedForRole protects owner shell from unauthorized roles', () {
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.owner, UserRole.owner), isTrue);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.ownerBays, UserRole.owner), isTrue);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.owner, UserRole.driver), isFalse);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.owner, UserRole.guard), isFalse);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.owner, null), isFalse);
    });

    test('isRouteAuthorizedForRole protects operations shell from unauthorized roles', () {
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.ops, UserRole.operations), isTrue);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.opsApprovals, UserRole.operations), isTrue);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.ops, UserRole.driver), isFalse);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.ops, UserRole.owner), isFalse);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.ops, UserRole.guard), isFalse);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.ops, null), isFalse);
    });

    test('isRouteAuthorizedForRole allows public authentication routes for unauthenticated users', () {
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.login, null), isTrue);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.otp, null), isTrue);
      expect(AppRouter.isRouteAuthorizedForRole(AppRouter.root, null), isTrue);
    });

    test('UserRoleExtension correctly parses role strings from backend claims', () {
      expect(UserRoleExtension.fromString('DRIVER'), equals(UserRole.driver));
      expect(UserRoleExtension.fromString('driver'), equals(UserRole.driver));
      expect(UserRoleExtension.fromString('SPACE_OWNER'), equals(UserRole.owner));
      expect(UserRoleExtension.fromString('OWNER'), equals(UserRole.owner));
      expect(UserRoleExtension.fromString('SECURITY_GUARD'), equals(UserRole.guard));
      expect(UserRoleExtension.fromString('GUARD'), equals(UserRole.guard));
      expect(UserRoleExtension.fromString('OPERATIONS'), equals(UserRole.operations));
      expect(UserRoleExtension.fromString('ADMIN'), equals(UserRole.operations));
      expect(UserRoleExtension.fromString('UNKNOWN_ROLE'), isNull);
      expect(UserRoleExtension.fromString(null), isNull);
    });
  });
}
