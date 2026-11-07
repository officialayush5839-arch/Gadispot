import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gadispot_mobile/core/config/env.dart';
import 'package:gadispot_mobile/core/network/api_client.dart';
import 'package:gadispot_mobile/core/routing/app_router.dart';
import 'package:gadispot_mobile/core/security/secure_storage_service.dart';
import 'package:gadispot_mobile/features/auth/data/auth_repository.dart';

void main() {
  group('AuthRepository Unit Tests', () {
    late SecureStorageService storage;
    late Dio customDio;
    late ApiClient apiClient;
    late AuthRepository authRepo;

    setUp(() {
      storage = InMemorySecureStorageService();
      customDio = Dio(BaseOptions(baseUrl: 'http://testserver'));
      apiClient = ApiClient(
        storageService: storage,
        envConfig: EnvConfig.dev(),
        customDio: customDio,
      );
      authRepo = AuthRepositoryImpl(
        apiClient: apiClient,
        storageService: storage,
      );
    });

    test('restoreSession returns null when no token is present', () async {
      final user = await authRepo.restoreSession();
      expect(user, isNull);
    });

    test('restoreSession parses stored token and role correctly', () async {
      await storage.saveAccessToken('test_jwt_access_token');
      await storage.saveUserId('usr-12345');
      await storage.saveUserRole('SPACE_OWNER');

      final user = await authRepo.restoreSession();
      expect(user, isNotNull);
      expect(user!.id, equals('usr-12345'));
      expect(user.activeRole, equals(UserRole.owner));
    });

    test('logout wipes secure storage completely', () async {
      await storage.saveAccessToken('token_to_wipe');
      await storage.saveRefreshToken('refresh_to_wipe');
      await storage.saveUserId('usr-wipe');

      await authRepo.logout();

      expect(await storage.getAccessToken(), isNull);
      expect(await storage.getRefreshToken(), isNull);
      expect(await storage.getUserId(), isNull);
    });
  });
}
