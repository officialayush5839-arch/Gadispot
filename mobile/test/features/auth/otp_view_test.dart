import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gadispot_mobile/core/routing/app_router.dart';
import 'package:gadispot_mobile/features/auth/data/auth_repository.dart';
import 'package:gadispot_mobile/features/auth/domain/auth_state.dart';
import 'package:gadispot_mobile/features/auth/presentation/otp_view.dart';

class MockSuccessAuthRepository implements AuthRepository {
  @override
  Future<AuthUser> exchangePhoneToken({required String idToken, String? fcmToken}) async {
    return const AuthUser(
      id: 'mock-user-1',
      phoneNumber: '+919876543210',
      activeRole: UserRole.driver,
      allowedRoles: [UserRole.driver],
    );
  }

  @override
  Future<void> logout() async {}

  @override
  Future<AuthUser?> restoreSession() async => null;

  @override
  Future<UserRole> switchRole(UserRole targetRole) async => targetRole;
}

void main() {
  group('OtpView Widget Tests (Hardened IAM)', () {
    testWidgets('OtpView renders input, resend timer, and no client-side role dropdown', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: OtpView(
            phoneNumber: '+919876543210',
          ),
        ),
      );

      // Verify header texts
      expect(find.text('Enter 6-digit OTP'), findsOneWidget);
      expect(find.textContaining('+919876543210'), findsOneWidget);

      // Insecure role dropdown must NOT exist
      expect(find.text('SELECT ACTIVE ROLE SHELL'), findsNothing);
      expect(find.byType(DropdownButtonFormField<UserRole>), findsNothing);

      // Verify button
      expect(find.text('VERIFY & ACCESS'), findsOneWidget);
    });

    testWidgets('OtpView validates 6-digit input before submission', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: OtpView(
            phoneNumber: '+919876543210',
          ),
        ),
      );

      await tester.tap(find.text('VERIFY & ACCESS'));
      await tester.pump();

      expect(find.text('Please enter 6-digit verification code'), findsOneWidget);
    });

    testWidgets('OtpView successfully navigates to driver shell on valid submission', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          routes: {
            AppRouter.driver: (_) => const Scaffold(body: Text('DRIVER_SHELL_ACTIVE')),
          },
          home: OtpView(
            phoneNumber: '+919876543210',
            authRepository: MockSuccessAuthRepository(),
          ),
        ),
      );

      // Enter 6 digits
      await tester.enterText(find.byType(TextFormField), '123456');
      await tester.tap(find.text('VERIFY & ACCESS'));
      await tester.pumpAndSettle();

      expect(find.text('DRIVER_SHELL_ACTIVE'), findsOneWidget);
    });
  });
}
