import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gadispot_mobile/core/theme/app_theme.dart';
import 'package:gadispot_mobile/features/operations/presentation/approvals_view.dart';
import 'package:gadispot_mobile/features/operations/presentation/ops_shell.dart';

void main() {
  group('Operations Review & Approvals Views (Phase 03)', () {
    testWidgets('OpsShell renders review tabs', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.darkTheme,
          home: const OpsShell(),
        ),
      );

      expect(find.byType(OpsShell), findsOneWidget);
      expect(find.text('Property Approvals'), findsOneWidget);
      expect(find.text('Manual Reviews'), findsOneWidget);
    });

    testWidgets('ApprovalsView displays pending properties and review cards', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.darkTheme,
          home: const ApprovalsView(),
        ),
      );

      expect(find.byType(ApprovalsView), findsOneWidget);
      expect(find.text('Property Approvals Queue'), findsOneWidget);
      expect(find.text('Brigade Gateway B3 Bay Listing'), findsOneWidget);
      expect(find.text('PENDING REVIEW'), findsWidgets);
    });
  });
}
