import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gadispot_mobile/core/theme/app_theme.dart';
import 'package:gadispot_mobile/core/widgets/offline_banner.dart';
import 'package:gadispot_mobile/core/widgets/qr_container.dart';
import 'package:gadispot_mobile/features/driver/presentation/driver_shell.dart';
import 'package:gadispot_mobile/features/guard/presentation/guard_shell.dart';
import 'package:gadispot_mobile/features/owner/presentation/owner_shell.dart';

void main() {
  group('Widget Tests (TSK-P7-006)', () {
    testWidgets('QrContainer renders tokens, bay id, vehicle plate, and timer', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: QrContainer(
              passToken: 'spx_ent_testtoken1234567890',
              spaceIdentifier: 'BAY-A12',
              vehiclePlate: 'KA01AB1234',
              timeRemainingText: '07:45',
              isConsumed: false,
            ),
          ),
        ),
      );

      // Verify header texts
      expect(find.text('BAY-A12'), findsOneWidget);
      expect(find.text('KA01AB1234'), findsOneWidget);
      expect(find.text('07:45'), findsOneWidget);
      expect(find.text('ACTIVE PASS'), findsOneWidget);
    });

    testWidgets('QrContainer displays consumed overlay when pass is burned', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: QrContainer(
              passToken: 'spx_ent_burnedtoken1234',
              spaceIdentifier: 'BAY-B04',
              vehiclePlate: 'KA05CD5678',
              isConsumed: true,
            ),
          ),
        ),
      );

      expect(find.text('CONSUMED'), findsOneWidget);
    });

    testWidgets('OfflineBanner displays subterranean offline status and sync count', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: OfflineBanner(
              isOffline: true,
              pendingSyncCount: 3,
            ),
          ),
        ),
      );

      expect(find.textContaining('OFFLINE MODE'), findsOneWidget);
      expect(find.textContaining('3 pending admissions'), findsOneWidget);
    });

    testWidgets('DriverShell renders navigation items correctly', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.darkTheme,
          home: const DriverShell(),
        ),
      );

      expect(find.byType(DriverShell), findsOneWidget);
      expect(find.text('Search'), findsOneWidget);
      expect(find.text('Bookings'), findsOneWidget);
      expect(find.text('Vehicles'), findsOneWidget);
    });

    testWidgets('GuardShell renders scanner navigation tabs', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.darkTheme,
          home: const GuardShell(),
        ),
      );

      expect(find.byType(GuardShell), findsOneWidget);
      expect(find.text('Scan Pass'), findsOneWidget);
      expect(find.text('Admissions'), findsOneWidget);
    });

    testWidgets('OwnerShell renders property and earnings navigation tabs', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.darkTheme,
          home: const OwnerShell(),
        ),
      );

      expect(find.byType(OwnerShell), findsOneWidget);
      expect(find.text('Overview'), findsOneWidget);
      expect(find.text('Bays'), findsOneWidget);
      expect(find.text('Earnings'), findsOneWidget);
    });
  });
}
