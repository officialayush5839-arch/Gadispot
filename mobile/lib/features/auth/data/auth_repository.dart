import 'package:dio/dio.dart';
import '../../../core/constants/api_endpoints.dart';
import '../../../core/errors/failure.dart';
import '../../../core/network/api_client.dart';
import '../../../core/routing/app_router.dart';
import '../../../core/security/secure_storage_service.dart';
import '../domain/auth_state.dart';

/// Contract for mobile authentication and session repository.
abstract class AuthRepository {
  Future<AuthUser> exchangePhoneToken({
    required String idToken,
    String? fcmToken,
  });

  Future<AuthUser?> restoreSession();

  Future<void> logout();

  Future<UserRole> switchRole(UserRole targetRole);
}

/// Production implementation interacting with FastAPI /api/v1/auth routes.
class AuthRepositoryImpl implements AuthRepository {
  final ApiClient apiClient;
  final SecureStorageService storageService;

  AuthRepositoryImpl({
    required this.apiClient,
    required this.storageService,
  });

  @override
  Future<AuthUser> exchangePhoneToken({
    required String idToken,
    String? fcmToken,
  }) async {
    try {
      final response = await apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.authSession,
        data: {
          'id_token': idToken,
          if (fcmToken != null) 'fcm_token': fcmToken,
        },
      );

      final data = response.data!;
      final accessToken = data['access_token'] as String;
      final refreshToken = data['refresh_token'] as String;
      final userData = data['user'] as Map<String, dynamic>;

      final userId = userData['id']?.toString() ?? '';
      final phone = userData['phone_number']?.toString() ?? '';
      final fullName = userData['full_name']?.toString();
      final rolesList = (userData['roles'] as List<dynamic>?)
              ?.map((r) => r.toString())
              .toList() ??
          ['DRIVER'];

      final parsedAllowedRoles = rolesList
          .map((r) => UserRoleExtension.fromString(r))
          .whereType<UserRole>()
          .toList();

      final primaryRole = parsedAllowedRoles.isNotEmpty
          ? parsedAllowedRoles.first
          : UserRole.driver;

      // Securely persist credentials in Keystore / Keychain
      await storageService.saveAccessToken(accessToken);
      await storageService.saveRefreshToken(refreshToken);
      await storageService.saveUserId(userId);
      await storageService.saveUserRole(primaryRole.roleName);

      return AuthUser(
        id: userId,
        phoneNumber: phone,
        name: fullName,
        activeRole: primaryRole,
        allowedRoles: parsedAllowedRoles,
      );
    } on Failure {
      rethrow;
    } on DioException catch (e) {
      throw ProblemDetailsInterceptor.mapDioExceptionToFailure(e);
    } catch (e) {
      throw ServerFailure(
        title: 'Authentication Error',
        message: 'Unexpected authentication error: $e',
        code: 'AUTH_ERROR',
      );
    }
  }

  @override
  Future<AuthUser?> restoreSession() async {
    try {
      final token = await storageService.getAccessToken();
      if (token == null || token.isEmpty) {
        return null;
      }

      final userId = await storageService.getUserId() ?? '';
      final storedRole = await storageService.getUserRole();
      final activeRole = UserRoleExtension.fromString(storedRole) ?? UserRole.driver;

      return AuthUser(
        id: userId,
        phoneNumber: '',
        name: null,
        activeRole: activeRole,
        allowedRoles: [activeRole],
      );
    } catch (e) {
      return null;
    }
  }

  @override
  Future<void> logout() async {
    try {
      final refreshToken = await storageService.getRefreshToken();
      await apiClient.post<dynamic>(
        ApiEndpoints.authLogout,
        data: {
          if (refreshToken != null) 'refresh_token': refreshToken,
        },
      );
    } catch (_) {
      // Continue cleanup even if server call fails
    } finally {
      await storageService.wipeAllOnLogout();
    }
  }

  @override
  Future<UserRole> switchRole(UserRole targetRole) async {
    try {
      final response = await apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.authSwitchRole,
        data: {'target_role': targetRole.roleName},
      );
      final data = response.data!;
      final activeRoleStr = data['active_role'] as String;
      final newRole = UserRoleExtension.fromString(activeRoleStr) ?? targetRole;
      await storageService.saveUserRole(newRole.roleName);
      return newRole;
    } on Failure {
      rethrow;
    } on DioException catch (e) {
      throw ProblemDetailsInterceptor.mapDioExceptionToFailure(e);
    }
  }
}
