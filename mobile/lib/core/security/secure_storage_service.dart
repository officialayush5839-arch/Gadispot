import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../constants/storage_keys.dart';

/// Abstract contract for secure credential storage.
abstract class SecureStorageService {
  Future<void> saveAccessToken(String token);
  Future<String?> getAccessToken();

  Future<void> saveRefreshToken(String token);
  Future<String?> getRefreshToken();

  Future<void> saveUserRole(String role);
  Future<String?> getUserRole();

  Future<void> saveUserId(String userId);
  Future<String?> getUserId();

  Future<void> clearTokens();
  Future<void> wipeAllOnLogout();

  Future<void> write(String key, String value);
  Future<String?> read(String key);
  Future<void> delete(String key);
  Future<void> deleteAll();
}

/// Production implementation backed by Android Keystore and iOS Keychain.
class FlutterSecureStorageServiceImpl implements SecureStorageService {
  final FlutterSecureStorage _storage;

  FlutterSecureStorageServiceImpl({FlutterSecureStorage? storage})
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(
                encryptedSharedPreferences: true,
              ),
              iOptions: IOSOptions(
                accessibility: KeychainAccessibility.first_unlock,
              ),
            );

  @override
  Future<void> saveAccessToken(String token) async {
    await write(StorageKeys.accessToken, token);
  }

  @override
  Future<String?> getAccessToken() async {
    return read(StorageKeys.accessToken);
  }

  @override
  Future<void> saveRefreshToken(String token) async {
    await write(StorageKeys.refreshToken, token);
  }

  @override
  Future<String?> getRefreshToken() async {
    return read(StorageKeys.refreshToken);
  }

  @override
  Future<void> saveUserRole(String role) async {
    await write(StorageKeys.activeRole, role);
  }

  @override
  Future<String?> getUserRole() async {
    return read(StorageKeys.activeRole);
  }

  @override
  Future<void> saveUserId(String userId) async {
    await write(StorageKeys.userId, userId);
  }

  @override
  Future<String?> getUserId() async {
    return read(StorageKeys.userId);
  }

  @override
  Future<void> clearTokens() async {
    await delete(StorageKeys.accessToken);
    await delete(StorageKeys.refreshToken);
  }

  @override
  Future<void> wipeAllOnLogout() async {
    await deleteAll();
  }

  @override
  Future<void> write(String key, String value) async {
    await _storage.write(key: key, value: value);
  }

  @override
  Future<String?> read(String key) async {
    return _storage.read(key: key);
  }

  @override
  Future<void> delete(String key) async {
    await _storage.delete(key: key);
  }

  @override
  Future<void> deleteAll() async {
    await _storage.deleteAll();
  }
}

/// In-memory implementation for isolated unit testing and environments without hardware keystore.
class InMemorySecureStorageService implements SecureStorageService {
  final Map<String, String> _memory = {};

  @override
  Future<void> saveAccessToken(String token) async {
    _memory[StorageKeys.accessToken] = token;
  }

  @override
  Future<String?> getAccessToken() async {
    return _memory[StorageKeys.accessToken];
  }

  @override
  Future<void> saveRefreshToken(String token) async {
    _memory[StorageKeys.refreshToken] = token;
  }

  @override
  Future<String?> getRefreshToken() async {
    return _memory[StorageKeys.refreshToken];
  }

  @override
  Future<void> saveUserRole(String role) async {
    _memory[StorageKeys.activeRole] = role;
  }

  @override
  Future<String?> getUserRole() async {
    return _memory[StorageKeys.activeRole];
  }

  @override
  Future<void> saveUserId(String userId) async {
    _memory[StorageKeys.userId] = userId;
  }

  @override
  Future<String?> getUserId() async {
    return _memory[StorageKeys.userId];
  }

  @override
  Future<void> clearTokens() async {
    _memory.remove(StorageKeys.accessToken);
    _memory.remove(StorageKeys.refreshToken);
  }

  @override
  Future<void> wipeAllOnLogout() async {
    _memory.clear();
  }

  @override
  Future<void> write(String key, String value) async {
    _memory[key] = value;
  }

  @override
  Future<String?> read(String key) async {
    return _memory[key];
  }

  @override
  Future<void> delete(String key) async {
    _memory.remove(key);
  }

  @override
  Future<void> deleteAll() async {
    _memory.clear();
  }
}
