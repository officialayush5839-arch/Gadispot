import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gadispot_mobile/core/network/api_client.dart';
import 'package:gadispot_mobile/core/security/secure_storage_service.dart';

class MockRefreshHttpAdapter implements HttpClientAdapter {
  int refreshCallCount = 0;
  final List<String> receivedAuthHeaders = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final path = options.path;
    if (path.contains('/api/v1/auth/refresh')) {
      refreshCallCount++;
      final payload = jsonEncode({
        'access_token': 'new_access_token_123',
        'refresh_token': 'new_refresh_token_123',
        'token_type': 'bearer',
        'expires_in': 900,
      });
      return ResponseBody.fromString(
        payload,
        200,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        },
      );
    }

    // Protected requests being retried with refreshed token
    final authHeader = options.headers['Authorization'] as String?;
    if (authHeader != null) {
      receivedAuthHeaders.add(authHeader);
    }

    final responsePayload = jsonEncode({'success': true, 'path': path});
    return ResponseBody.fromString(
      responsePayload,
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

class TestErrorInterceptorHandler extends ErrorInterceptorHandler {
  DioException? passedError;
  Response<dynamic>? resolvedResponse;

  @override
  void next(DioException err) {
    passedError = err;
  }

  @override
  void resolve(Response<dynamic> response) {
    resolvedResponse = response;
  }

  @override
  void reject(DioException err, [bool? callNext]) {
    passedError = err;
  }
}

void main() {
  group('RefreshTokenInterceptor Tests', () {
    late SecureStorageService storage;
    late Dio dio;
    late RefreshTokenInterceptor interceptor;

    setUp(() {
      storage = InMemorySecureStorageService();
      dio = Dio(BaseOptions(baseUrl: 'http://testserver'));
      interceptor = RefreshTokenInterceptor(dio: dio, storageService: storage);
    });

    test('ignores 401 on auth endpoints to prevent recursion loops', () async {
      final authPaths = [
        '/api/v1/auth/session',
        '/api/v1/auth/exchange',
        '/api/v1/auth/firebase-exchange',
        '/api/v1/auth/refresh',
        '/api/v1/auth/logout',
        '/api/v1/auth/switch-role',
        '/api/v1/auth/2fa/setup',
        '/api/v1/auth/2fa/verify',
      ];

      for (final p in authPaths) {
        final reqOptions = RequestOptions(path: p);
        final dioErr = DioException(
          requestOptions: reqOptions,
          response: Response(requestOptions: reqOptions, statusCode: 401),
          type: DioExceptionType.badResponse,
        );

        final handler = TestErrorInterceptorHandler();
        await interceptor.onError(dioErr, handler);
        expect(handler.passedError, equals(dioErr));
      }
    });

    test('forwards 401 without refresh when refresh token is absent', () async {
      await storage.saveAccessToken('expired_access_token');
      // No refresh token saved

      final reqOptions = RequestOptions(
        baseUrl: 'http://testserver',
        path: '/api/v1/spaces/search',
        headers: {'Authorization': 'Bearer expired_access_token'},
      );
      final dioErr = DioException(
        requestOptions: reqOptions,
        response: Response(requestOptions: reqOptions, statusCode: 401),
        type: DioExceptionType.badResponse,
      );

      final handler = TestErrorInterceptorHandler();
      await interceptor.onError(dioErr, handler);

      expect(handler.passedError, equals(dioErr));
      expect(await storage.getAccessToken(), equals('expired_access_token'));
    });

    test('wipes storage when refresh call fails', () async {
      await storage.saveAccessToken('expired_access_token');
      await storage.saveRefreshToken('invalid_refresh_token');

      final reqOptions = RequestOptions(
        baseUrl: 'http://testserver',
        path: '/api/v1/spaces/search',
        headers: {'Authorization': 'Bearer expired_access_token'},
      );
      final dioErr = DioException(
        requestOptions: reqOptions,
        response: Response(requestOptions: reqOptions, statusCode: 401),
        type: DioExceptionType.badResponse,
      );

      final handler = TestErrorInterceptorHandler();
      await interceptor.onError(dioErr, handler);

      expect(handler.passedError, equals(dioErr));
      // Secure storage should be wiped on refresh failure
      expect(await storage.getAccessToken(), isNull);
      expect(await storage.getRefreshToken(), isNull);
    });

    test('concurrent 401s coordinate on shared refresh completer', () async {
      await storage.saveAccessToken('expired_access_token');
      await storage.saveRefreshToken('invalid_refresh_token');

      final req1 = RequestOptions(
        baseUrl: 'http://testserver',
        path: '/api/v1/spaces/search',
        headers: {'Authorization': 'Bearer expired_access_token'},
      );
      final req2 = RequestOptions(
        baseUrl: 'http://testserver',
        path: '/api/v1/bookings',
        headers: {'Authorization': 'Bearer expired_access_token'},
      );

      final dioErr1 = DioException(
        requestOptions: req1,
        response: Response(requestOptions: req1, statusCode: 401),
        type: DioExceptionType.badResponse,
      );
      final dioErr2 = DioException(
        requestOptions: req2,
        response: Response(requestOptions: req2, statusCode: 401),
        type: DioExceptionType.badResponse,
      );

      final handler1 = TestErrorInterceptorHandler();
      final handler2 = TestErrorInterceptorHandler();

      // Launch both concurrently
      await Future.wait([
        interceptor.onError(dioErr1, handler1),
        interceptor.onError(dioErr2, handler2),
      ]);

      // Both should have cleanly handled the failure without throwing or hanging
      expect(handler1.passedError, equals(dioErr1));
      expect(handler2.passedError, equals(dioErr2));
      expect(await storage.getAccessToken(), isNull);
      expect(await storage.getRefreshToken(), isNull);
    });

    test('concurrent 401s coordinate on single refresh and retry successfully', () async {
      final mockAdapter = MockRefreshHttpAdapter();
      dio.httpClientAdapter = mockAdapter;

      await storage.saveAccessToken('expired_access_token');
      await storage.saveRefreshToken('valid_refresh_token');

      final req1 = RequestOptions(
        baseUrl: 'http://testserver',
        path: '/api/v1/spaces/search',
        headers: {'Authorization': 'Bearer expired_access_token'},
      );
      final req2 = RequestOptions(
        baseUrl: 'http://testserver',
        path: '/api/v1/bookings',
        headers: {'Authorization': 'Bearer expired_access_token'},
      );

      final dioErr1 = DioException(
        requestOptions: req1,
        response: Response(requestOptions: req1, statusCode: 401),
        type: DioExceptionType.badResponse,
      );
      final dioErr2 = DioException(
        requestOptions: req2,
        response: Response(requestOptions: req2, statusCode: 401),
        type: DioExceptionType.badResponse,
      );

      final handler1 = TestErrorInterceptorHandler();
      final handler2 = TestErrorInterceptorHandler();

      // Launch both 401 handlers concurrently
      await Future.wait([
        interceptor.onError(dioErr1, handler1),
        interceptor.onError(dioErr2, handler2),
      ]);

      // 1. Only ONE refresh request is made across all concurrent callers
      expect(mockAdapter.refreshCallCount, equals(1));

      // 2. Both original requests retry with the new access token
      expect(mockAdapter.receivedAuthHeaders.length, equals(2));
      expect(mockAdapter.receivedAuthHeaders[0], equals('Bearer new_access_token_123'));
      expect(mockAdapter.receivedAuthHeaders[1], equals('Bearer new_access_token_123'));

      // 3. Both receive successful (resolved) responses
      expect(handler1.resolvedResponse?.statusCode, equals(200));
      expect(handler2.resolvedResponse?.statusCode, equals(200));
      expect(handler1.passedError, isNull);
      expect(handler2.passedError, isNull);

      // 4. Tokens remain stored correctly in secure storage
      expect(await storage.getAccessToken(), equals('new_access_token_123'));
      expect(await storage.getRefreshToken(), equals('new_refresh_token_123'));
    });
  });
}

