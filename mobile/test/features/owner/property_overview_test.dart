import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gadispot_mobile/core/theme/app_theme.dart';
import 'package:gadispot_mobile/features/owner/presentation/property_overview_view.dart';
import 'package:gadispot_mobile/features/owner/presentation/bay_management_view.dart';

void main() {
  group('Owner Property & Inventory Views (Phase 03)', () {
    testWidgets('PropertyOverviewView displays property details and live metrics', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.darkTheme,
          home: const PropertyOverviewView(),
        ),
      );

      expect(find.byType(PropertyOverviewView), findsOneWidget);
      expect(find.text('Property Overview'), findsOneWidget);
      expect(find.text('Koramangala Residency Driveway'), findsOneWidget);
      expect(find.text('VERIFIED & PUBLISHED'), findsOneWidget);
      expect(find.text('TOTAL BAYS'), findsOneWidget);
      expect(find.text('TODAY OCCUPANCY'), findsOneWidget);
    });

    testWidgets('BayManagementView displays inventory list and bay details', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.darkTheme,
          home: const BayManagementView(),
        ),
      );

      expect(find.byType(BayManagementView), findsOneWidget);
      expect(find.text('Bay Inventory & Pricing'), findsOneWidget);
      expect(find.text('Add New Bay'), findsOneWidget);
    });
  });
}
