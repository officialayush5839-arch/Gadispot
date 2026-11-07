import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gadispot_mobile/core/routing/app_router.dart';
import 'package:gadispot_mobile/core/widgets/role_switcher.dart';

void main() {
  group('RoleSwitcher Widget Tests', () {
    testWidgets('RoleSwitcher renders both pills when user has driver and owner roles', (tester) async {
      UserRole? toggledRole;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RoleSwitcher(
              activeRole: UserRole.driver,
              allowedRoles: const [UserRole.driver, UserRole.owner],
              onRoleChanged: (role) => toggledRole = role,
            ),
          ),
        ),
      );

      expect(find.text('DRIVER'), findsOneWidget);
      expect(find.text('SPACE OWNER'), findsOneWidget);

      // Tap on SPACE OWNER
      await tester.tap(find.text('SPACE OWNER'));
      await tester.pumpAndSettle();

      expect(toggledRole, equals(UserRole.owner));
    });

    testWidgets('RoleSwitcher hides when user only has single role', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RoleSwitcher(
              activeRole: UserRole.driver,
              allowedRoles: const [UserRole.driver],
              onRoleChanged: (_) {},
            ),
          ),
        ),
      );

      expect(find.text('DRIVER'), findsNothing);
      expect(find.text('SPACE OWNER'), findsNothing);
    });
  });
}
