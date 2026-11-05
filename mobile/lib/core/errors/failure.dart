/// Domain failure models and RFC 7807 Problem Details representation.

abstract class Failure implements Exception {
  final String message;
  final String code;
  final int? statusCode;
  final String? typeUri;
  final String? instance;
  final Map<String, dynamic>? details;

  const Failure({
    required this.message,
    required this.code,
    this.statusCode,
    this.typeUri,
    this.instance,
    this.details,
  });

  @override
  String toString() => '$runtimeType(code: $code, statusCode: $statusCode, message: $message)';
}

/// Network layer failures (connection loss, timeouts, dead-zones)
class NetworkFailure extends Failure {
  final bool isSubterraneanDeadZone;

  const NetworkFailure({
    required String message,
    String code = 'NETWORK_ERROR',
    int? statusCode,
    this.isSubterraneanDeadZone = false,
  }) : super(
          message: message,
          code: code,
          statusCode: statusCode,
        );

  factory NetworkFailure.timeout([String message = 'Connection timed out. Please check your connectivity.']) {
    return NetworkFailure(message: message, code: 'TIMEOUT');
  }

  factory NetworkFailure.offline([String message = 'Subterranean dead zone detected. Running in offline pass mode.']) {
    return NetworkFailure(
      message: message,
      code: 'OFFLINE_DEAD_ZONE',
      isSubterraneanDeadZone: true,
    );
  }
}

/// Authentication and authorization failures
class AuthFailure extends Failure {
  const AuthFailure({
    required String message,
    String code = 'AUTH_ERROR',
    int? statusCode = 401,
  }) : super(
          message: message,
          code: code,
          statusCode: statusCode,
        );

  factory AuthFailure.unauthorized([String message = 'Session expired or unauthenticated. Please log in again.']) {
    return AuthFailure(message: message, code: 'UNAUTHORIZED', statusCode: 401);
  }

  factory AuthFailure.forbidden([String message = 'Insufficient privileges for this role action.']) {
    return AuthFailure(message: message, code: 'FORBIDDEN', statusCode: 403);
  }

  factory AuthFailure.invalidToken([String message = 'Invalid or expired Firebase/JWT token.']) {
    return AuthFailure(message: message, code: 'INVALID_TOKEN', statusCode: 401);
  }
}

/// Server-side RFC 7807 Problem Details representation
class ServerFailure extends Failure {
  final String title;
  final String? problemTimestamp;

  const ServerFailure({
    required String message,
    required String code,
    required this.title,
    int? statusCode,
    String? typeUri,
    String? instance,
    this.problemTimestamp,
    Map<String, dynamic>? details,
  }) : super(
          message: message,
          code: code,
          statusCode: statusCode,
          typeUri: typeUri,
          instance: instance,
          details: details,
        );

  /// Parse compliant RFC 7807 Problem Details payload
  /// Example:
  /// {
  ///   "type": "https://api.gadispot.in/errors/CONFLICT",
  ///   "title": "State Conflict",
  ///   "status": 409,
  ///   "detail": "The selected parking space was claimed by another driver.",
  ///   "code": "SLOT_ALREADY_RESERVED",
  ///   "instance": "/api/v1/bookings/hold",
  ///   "timestamp": "2026-11-05T11:35:00Z"
  /// }
  factory ServerFailure.fromProblemDetails(
    Map<String, dynamic> json, {
    int? fallbackStatusCode,
  }) {
    final status = (json['status'] as num?)?.toInt() ?? fallbackStatusCode ?? 500;
    final code = json['code']?.toString() ?? 'SERVER_ERROR';
    final title = json['title']?.toString() ?? 'Server Error';
    final detail = json['detail']?.toString() ?? json['message']?.toString() ?? 'An unexpected error occurred.';
    final typeUri = json['type']?.toString();
    final instance = json['instance']?.toString();
    final timestamp = json['timestamp']?.toString();

    // Extract extra error fields if any
    final extra = Map<String, dynamic>.from(json);
    extra.remove('type');
    extra.remove('title');
    extra.remove('status');
    extra.remove('detail');
    extra.remove('code');
    extra.remove('instance');
    extra.remove('timestamp');

    return ServerFailure(
      message: detail,
      code: code,
      title: title,
      statusCode: status,
      typeUri: typeUri,
      instance: instance,
      problemTimestamp: timestamp,
      details: extra.isNotEmpty ? extra : null,
    );
  }
}

/// Keystore / Keychain secure storage failure
class StorageFailure extends Failure {
  const StorageFailure({
    required String message,
    String code = 'STORAGE_ERROR',
  }) : super(
          message: message,
          code: code,
        );
}

/// Client-side validation failure
class ValidationFailure extends Failure {
  final Map<String, String>? fieldErrors;

  const ValidationFailure({
    required String message,
    String code = 'VALIDATION_ERROR',
    this.fieldErrors,
  }) : super(
          message: message,
          code: code,
        );
}
