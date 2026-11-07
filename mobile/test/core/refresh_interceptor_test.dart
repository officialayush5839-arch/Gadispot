import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gadispot_mobile/core/network/api_client.dart';
import 'package:gadispot_mobile/core/security/secure_storage_service.dart';

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
      final reqOptions = RequestOptions(path: '/api/v1/auth/session');
      final dioErr = DioException(
        requestOptions: reqOptions,
        response: Response(requestOptions: reqOptions, statusCode: 401),
        type: DioExceptionType.badResponse,
      );

      final handler = TestErrorInterceptorHandler();
      await interceptor.onError(dioErr, handler);

      expect(handler.passedError, equals(dioErr));
    });

    test('forwards 401 without refresh when refresh token is absent', () async {
      await storage.saveAccessToken('expired_access_token');
      // No refresh token saved

      final reqOptions = RequestOptions(path: '/api/v1/spaces/search');
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

      final reqOptions = RequestOptions(path: '/api/v1/spaces/search');
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
  });
}

