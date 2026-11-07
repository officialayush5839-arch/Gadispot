import 'dart:async';
import 'dart:math';
import 'package:dio/dio.dart';
import '../config/env.dart';
import '../errors/failure.dart';
import '../security/secure_storage_service.dart';

/// UUID v4 generator for X-Request-ID and Idempotency-Key headers without external dependencies.
class UuidGenerator {
  static final Random _secureRandom = Random.secure();

  static String generateV4() {
    final values = List<int>.generate(16, (i) => _secureRandom.nextInt(256));
    // Set version to 4
    values[6] = (values[6] & 0x0f) | 0x40;
    // Set variant to RFC 4122 (10xxxxxx)
    values[8] = (values[8] & 0x3f) | 0x80;

    final hex = values.map((b) => b.toRadixString(16).padLeft(2, '0')).toList();
    return '${hex[0]}${hex[1]}${hex[2]}${hex[3]}-'
        '${hex[4]}${hex[5]}-'
        '${hex[6]}${hex[7]}-'
        '${hex[8]}${hex[9]}-'
        '${hex[10]}${hex[11]}${hex[12]}${hex[13]}${hex[14]}${hex[15]}';
  }
}

/// Request-ID generator and propagator interceptor.
class RequestIdInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    if (!options.headers.containsKey('X-Request-ID')) {
      options.headers['X-Request-ID'] = UuidGenerator.generateV4();
    }
    handler.next(options);
  }
}

/// Bearer token injection interceptor.
class AuthInterceptor extends Interceptor {
  final SecureStorageService _storageService;

  AuthInterceptor(this._storageService);

  @override
  Future<void> onRequest(
      RequestOptions options, RequestInterceptorHandler handler) async {
    // Skip auth header if already provided or if path is public health/exchange
    if (!options.headers.containsKey('Authorization')) {
      final token = await _storageService.getAccessToken();
      if (token != null && token.isNotEmpty) {
        options.headers['Authorization'] = 'Bearer $token';
      }
    }
    handler.next(options);
  }
}

/// Interceptor that intercepts HTTP 401 Unauthorized errors to perform automatic
/// background token refresh using the stored refresh token and retry the original request.
class RefreshTokenInterceptor extends QueuedInterceptor {
  final Dio dio;
  final SecureStorageService storageService;
  Completer<String?>? _refreshCompleter;

  RefreshTokenInterceptor({
    required this.dio,
    required this.storageService,
  });

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    final response = err.response;
    final path = err.requestOptions.path;

    // Do not attempt refresh on auth endpoints to prevent endless loops
    final isAuthEndpoint = path.contains('/auth/session') ||
        path.contains('/auth/exchange') ||
        path.contains('/auth/firebase-exchange') ||
        path.contains('/auth/refresh') ||
        path.contains('/auth/logout') ||
        path.contains('/auth/switch-role') ||
        path.contains('/auth/2fa/');

    if (response?.statusCode == 401 && !isAuthEndpoint) {
      // 1. Check if token was already refreshed by another concurrent request
      final storedAccess = await storageService.getAccessToken();
      final currentHeader = err.requestOptions.headers['Authorization'] as String?;
      if (currentHeader != null &&
          storedAccess != null &&
          storedAccess.isNotEmpty &&
          currentHeader != 'Bearer $storedAccess') {
        final options = err.requestOptions;
        if (options.baseUrl.isEmpty) {
          options.baseUrl = dio.options.baseUrl;
        }
        options.headers['Authorization'] = 'Bearer $storedAccess';
        try {
          final retryResponse = await dio.fetch<dynamic>(options);
          return handler.resolve(retryResponse);
        } catch (retryErr) {
          if (retryErr is DioException) {
            return handler.next(retryErr);
          }
        }
      }

      // 2. Coordinated token refresh using shared Completer for parallel 401s
      if (_refreshCompleter != null) {
        try {
          final refreshedToken = await _refreshCompleter!.future;
          if (refreshedToken != null && refreshedToken.isNotEmpty) {
            final options = err.requestOptions;
            if (options.baseUrl.isEmpty) {
              options.baseUrl = dio.options.baseUrl;
            }
            options.headers['Authorization'] = 'Bearer $refreshedToken';
            final retryResponse = await dio.fetch<dynamic>(options);
            return handler.resolve(retryResponse);
          }
        } catch (retryErr) {
          if (retryErr is DioException) {
            return handler.next(retryErr);
          }
        }
        return handler.next(err);
      }

      // 3. Initiate single refresh operation for all queued concurrent 401s
      final completer = Completer<String?>();
      _refreshCompleter = completer;

      try {
        final refreshToken = await storageService.getRefreshToken();
        if (refreshToken != null && refreshToken.isNotEmpty) {
          final refreshDio = Dio(
            BaseOptions(
              baseUrl: dio.options.baseUrl,
              connectTimeout: const Duration(seconds: 10),
              receiveTimeout: const Duration(seconds: 10),
              headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
              },
            ),
          );
          refreshDio.httpClientAdapter = dio.httpClientAdapter;

          final refreshResp = await refreshDio.post<Map<String, dynamic>>(
            '/api/v1/auth/refresh',
            data: {'refresh_token': refreshToken},
          );

          if (refreshResp.statusCode == 200 && refreshResp.data != null) {
            final data = refreshResp.data!;
            final newAccess = data['access_token'] as String;
            final newRefresh = data['refresh_token'] as String;

            await storageService.saveAccessToken(newAccess);
            await storageService.saveRefreshToken(newRefresh);

            completer.complete(newAccess);

            final options = err.requestOptions;
            if (options.baseUrl.isEmpty) {
              options.baseUrl = dio.options.baseUrl;
            }
            options.headers['Authorization'] = 'Bearer $newAccess';

            final retryResponse = await dio.fetch<dynamic>(options);
            return handler.resolve(retryResponse);
          } else {
            completer.complete(null);
          }
        } else {
          completer.complete(null);
        }
      } catch (refreshError) {
        // Refresh token compromised, expired, or reuse detected: wipe tokens
        await storageService.wipeAllOnLogout();
        completer.complete(null);
      } finally {
        _refreshCompleter = null;
      }
    }

    handler.next(err);
  }
}

/// Interceptor that translates HTTP and network errors into typed Failure objects,
/// parsing RFC 7807 Problem Details payloads when available.
class ProblemDetailsInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final failure = mapDioExceptionToFailure(err);
    // Attach failure to error request options extra for caller retrieval
    err.requestOptions.extra['failure'] = failure;
    handler.next(err);
  }

  static Failure mapDioExceptionToFailure(DioException err) {
    // 1. Connection / Timeout errors
    if (err.type == DioExceptionType.connectionTimeout ||
        err.type == DioExceptionType.sendTimeout ||
        err.type == DioExceptionType.receiveTimeout) {
      return NetworkFailure.timeout(
        'Request timed out after ${err.requestOptions.connectTimeout?.inSeconds ?? 10} seconds.',
      );
    }

    if (err.type == DioExceptionType.connectionError) {
      return const NetworkFailure(
        message: 'Unable to reach Gadispot server. Subterranean cellular dead zone or no internet.',
        code: 'CONNECTION_FAILED',
        isSubterraneanDeadZone: true,
      );
    }

    // 2. Server response errors (Status code 4xx / 5xx)
    final response = err.response;
    if (response != null) {
      final statusCode = response.statusCode ?? 500;
      final data = response.data;

      // Check if response body is RFC 7807 Problem Details JSON
      if (data is Map<String, dynamic>) {
        if (data.containsKey('type') ||
            data.containsKey('title') ||
            data.containsKey('code') ||
            data.containsKey('detail')) {
          final serverFailure = ServerFailure.fromProblemDetails(
            data,
            fallbackStatusCode: statusCode,
          );

          // Route to AuthFailure for 401/403 if applicable
          if (statusCode == 401) {
            return AuthFailure.unauthorized(serverFailure.message);
          }
          if (statusCode == 403) {
            return AuthFailure.forbidden(serverFailure.message);
          }
          return serverFailure;
        }
      }

      // Fallback for non-RFC7807 status responses
      if (statusCode == 401) {
        return AuthFailure.unauthorized();
      }
      if (statusCode == 403) {
        return AuthFailure.forbidden();
      }
      return ServerFailure(
        message: response.statusMessage ?? 'Server returned HTTP $statusCode',
        code: 'HTTP_$statusCode',
        title: 'HTTP Error',
        statusCode: statusCode,
      );
    }

    // 3. Fallback generic failure
    return NetworkFailure(
      message: err.message ?? 'Unknown network failure occurred.',
      code: 'UNKNOWN_NETWORK_ERROR',
    );
  }
}

/// Centralized Dio API Client for Gadispot Mobile Application.
class ApiClient {
  final Dio dio;
  final SecureStorageService storageService;
  final EnvConfig envConfig;

  ApiClient({
    required this.storageService,
    EnvConfig? envConfig,
    Dio? customDio,
  })  : envConfig = envConfig ?? EnvConfig.current,
        dio = customDio ??
            Dio(
              BaseOptions(
                baseUrl: (envConfig ?? EnvConfig.current).baseUrl,
                connectTimeout: (envConfig ?? EnvConfig.current).connectTimeout,
                receiveTimeout: (envConfig ?? EnvConfig.current).receiveTimeout,
                sendTimeout: (envConfig ?? EnvConfig.current).sendTimeout,
                headers: {
                  'Accept': 'application/json',
                  'Content-Type': 'application/json',
                },
              ),
            ) {
    _setupInterceptors();
  }

  void _setupInterceptors() {
    dio.interceptors.addAll([
      RequestIdInterceptor(),
      AuthInterceptor(storageService),
      RefreshTokenInterceptor(dio: dio, storageService: storageService),
      ProblemDetailsInterceptor(),
    ]);
  }

  /// Execute GET request
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    try {
      return await dio.get<T>(
        path,
        queryParameters: queryParameters,
        options: options,
        cancelToken: cancelToken,
      );
    } on DioException catch (e) {
      throw _extractFailure(e);
    }
  }

  /// Execute POST request with optional Idempotency-Key
  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    String? idempotencyKey,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    try {
      final requestOptions = options ?? Options();
      if (idempotencyKey != null) {
        requestOptions.headers = {
          ...?requestOptions.headers,
          'Idempotency-Key': idempotencyKey,
        };
      }
      return await dio.post<T>(
        path,
        data: data,
        queryParameters: queryParameters,
        options: requestOptions,
        cancelToken: cancelToken,
      );
    } on DioException catch (e) {
      throw _extractFailure(e);
    }
  }

  /// Execute PUT request
  Future<Response<T>> put<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    try {
      return await dio.put<T>(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
        cancelToken: cancelToken,
      );
    } on DioException catch (e) {
      throw _extractFailure(e);
    }
  }

  /// Execute DELETE request
  Future<Response<T>> delete<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    try {
      return await dio.delete<T>(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
        cancelToken: cancelToken,
      );
    } on DioException catch (e) {
      throw _extractFailure(e);
    }
  }

  Failure _extractFailure(DioException e) {
    if (e.requestOptions.extra.containsKey('failure')) {
      final f = e.requestOptions.extra['failure'];
      if (f is Failure) return f;
    }
    return ProblemDetailsInterceptor.mapDioExceptionToFailure(e);
  }
}
