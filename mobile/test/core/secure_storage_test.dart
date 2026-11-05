import 'package:flutter_test/flutter_test.dart';
import 'package:gadispot_mobile/core/constants/storage_keys.dart';
import 'package:gadispot_mobile/core/security/secure_storage_service.dart';

void main() {
  group('SecureStorageService Unit Tests', () {
    late SecureStorageService storage;

    setUp(() {
      storage = InMemorySecureStorageService();
    });

    test('should save and retrieve access token correctly', () async {
      const token = 'header.payload.signature_jwt_access';
      await storage.saveAccessToken(token);

      final retrieved = await storage.getAccessToken();
      expect(retrieved, equals(token));
    });

    test('should save and retrieve refresh token correctly', () async {
      const refreshToken = 'header.payload.signature_jwt_refresh';
      await storage.saveRefreshToken(refreshToken);

      final retrieved = await storage.getRefreshToken();
      expect(retrieved, equals(refreshToken));
    });

    test('should save and retrieve active user role', () async {
      await storage.saveUserRole('SECURITY_GUARD');

      final role = await storage.getUserRole();
      expect(role, equals('SECURITY_GUARD'));
    });

    test('should save and retrieve user id', () async {
      const userId = 'usr_01H1234567890ABCDEF';
      await storage.saveUserId(userId);

      final retrieved = await storage.getUserId();
      expect(retrieved, equals(userId));
    });

    test('clearTokens should only delete access and refresh tokens, preserving role and id', () async {
      await storage.saveAccessToken('token_123');
      await storage.saveRefreshToken('refresh_456');
      await storage.saveUserRole('SPACE_OWNER');
      await storage.saveUserId('usr_999');

      await storage.clearTokens();

      expect(await storage.getAccessToken(), isNull);
      expect(await storage.getRefreshToken(), isNull);
      expect(await storage.getUserRole(), equals('SPACE_OWNER'));
      expect(await storage.getUserId(), equals('usr_999'));
    });

    test('wipeAllOnLogout should purge all stored keys and credentials completely', () async {
      await storage.saveAccessToken('token_123');
      await storage.saveRefreshToken('refresh_456');
      await storage.saveUserRole('DRIVER');
      await storage.saveUserId('usr_111');
      await storage.write(StorageKeys.offlinePassCache, 'cached_pass_json');

      await storage.wipeAllOnLogout();

      expect(await storage.getAccessToken(), isNull);
      expect(await storage.getRefreshToken(), isNull);
      expect(await storage.getUserRole(), isNull);
      expect(await storage.getUserId(), isNull);
      expect(await storage.read(StorageKeys.offlinePassCache), isNull);
    });
  });
}
