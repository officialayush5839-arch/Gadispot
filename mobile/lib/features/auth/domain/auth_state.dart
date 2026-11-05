import '../../../core/errors/failure.dart';
import '../../../core/routing/app_router.dart';

/// Authentication state model representing the current user session.
enum AuthStatus {
  initial,
  loading,
  authenticated,
  unauthenticated,
  error,
}

class AuthUser {
  final String id;
  final String phoneNumber;
  final String? name;
  final UserRole activeRole;
  final List<UserRole> allowedRoles;

  const AuthUser({
    required this.id,
    required this.phoneNumber,
    this.name,
    required this.activeRole,
    this.allowedRoles = const [],
  });

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    final activeRoleStr = json['active_role'] as String? ?? 'DRIVER';
    final allowedRolesList = (json['allowed_roles'] as List<dynamic>?)
            ?.map((r) => UserRoleExtension.fromString(r.toString()))
            .whereType<UserRole>()
            .toList() ??
        [UserRole.driver];

    return AuthUser(
      id: json['id']?.toString() ?? '',
      phoneNumber: json['phone_number']?.toString() ?? '',
      name: json['name']?.toString(),
      activeRole: UserRoleExtension.fromString(activeRoleStr) ?? UserRole.driver,
      allowedRoles: allowedRolesList,
    );
  }
}

class AuthState {
  final AuthStatus status;
  final AuthUser? user;
  final Failure? failure;

  const AuthState({
    required this.status,
    this.user,
    this.failure,
  });

  factory AuthState.initial() => const AuthState(status: AuthStatus.initial);

  factory AuthState.loading() => const AuthState(status: AuthStatus.loading);

  factory AuthState.authenticated(AuthUser user) => AuthState(
        status: AuthStatus.authenticated,
        user: user,
      );

  factory AuthState.unauthenticated() => const AuthState(
        status: AuthStatus.unauthenticated,
      );

  factory AuthState.error(Failure failure) => AuthState(
        status: AuthStatus.error,
        failure: failure,
      );

  bool get isAuthenticated => status == AuthStatus.authenticated && user != null;
}
