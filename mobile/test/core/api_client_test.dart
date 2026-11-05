import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gadispot_mobile/core/config/env.dart';
import 'package:gadispot_mobile/core/errors/failure.dart';
import 'package:gadispot_mobile/core/network/api_client.dart';
import 'package:gadispot_mobile/core/security/secure_storage_service.dart';

void main() {
  group('ApiClient & Network Architecture Tests', () {
    late SecureStorageService storage;
    late EnvConfig devConfig;

    setUp(() {
      storage = InMemorySecureStorageService();
      devConfig = EnvConfig.dev();
    });

    test('UuidGenerator produces compliant RFC 4122 version 4 UUIDs', () {
      final uuid = UuidGenerator.generateV4();
      expect(uuid.length, equals(36));
      expect(uuid[14], equals('4')); // Version 4
      expect(['8', '9', 'a', 'b'].contains(uuid[19].toLowerCase()), isTrue); // RFC 4122 variant
      expect(
        RegExp(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', caseSensitive: false)
            .hasMatch(uuid),
        isTrue,
      );
    });

    test('RequestIdInterceptor automatically attaches X-Request-ID header', () {
      final interceptor = RequestIdInterceptor();
      final options = RequestOptions(path: '/test');

      interceptor.onRequest(options, RequestInterceptorHandler());

      expect(options.headers.containsKey('X-Request-ID'), isTrue);
      expect(options.headers['X-Request-ID'].toString().length, equals(36));
    });

    test('AuthInterceptor injects Bearer token when present in storage', () async {
      const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0';
      await storage.saveAccessToken(token);

      final interceptor = AuthInterceptor(storage);
      final options = RequestOptions(path: '/api/v1/bookings/active');

      await interceptor.onRequest(options, RequestInterceptorHandler());

      expect(options.headers['Authorization'], equals('Bearer $token'));
    });

    test('AuthInterceptor does not overwrite existing Authorization header', () async {
      await storage.saveAccessToken('default_token');

      final interceptor = AuthInterceptor(storage);
      final options = RequestOptions(
        path: '/api/v1/test',
        headers: {'Authorization': 'Bearer custom_override_token'},
      );

      await interceptor.onRequest(options, RequestInterceptorHandler());

      expect(options.headers['Authorization'], equals('Bearer custom_override_token'));
    });

    test('ProblemDetailsInterceptor parses RFC 7807 409 Conflict into ServerFailure', () {
      final problemJson = {
        'type': 'https://api.gadispot.in/errors/CONFLICT',
        'title': 'State Conflict',
        'status': 409,
        'detail': 'The selected parking space was claimed by another driver.',
        'code': 'SLOT_ALREADY_RESERVED',
        'instance': '/api/v1/bookings/hold',
        'timestamp': '2026-11-05T11:35:00Z',
      };

      final dioError = DioException(
        requestOptions: RequestOptions(path: '/api/v1/bookings/hold'),
        response: Response(
          requestOptions: RequestOptions(path: '/api/v1/bookings/hold'),
          statusCode: 409,
          data: problemJson,
        ),
        type: DioExceptionType.badResponse,
      );

      final failure = ProblemDetailsInterceptor.mapDioExceptionToFailure(dioError);

      expect(failure, isA<ServerFailure>());
      final serverFailure = failure as ServerFailure;
      expect(serverFailure.statusCode, equals(409));
      expect(serverFailure.code, equals('SLOT_ALREADY_RESERVED'));
      expect(serverFailure.title, equals('State Conflict'));
      expect(serverFailure.message, equals('The selected parking space was claimed by another driver.'));
      expect(serverFailure.instance, equals('/api/v1/bookings/hold'));
      expect(serverFailure.typeUri, equals('https://api.gadispot.in/errors/CONFLICT'));
    });

    test('ProblemDetailsInterceptor translates 401 response into AuthFailure.unauthorized', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/api/v1/bookings/active'),
        response: Response(
          requestOptions: RequestOptions(path: '/api/v1/bookings/active'),
          statusCode: 401,
          data: {
            'type': 'https://api.gadispot.in/errors/UNAUTHORIZED',
            'title': 'Unauthorized',
            'status': 401,
            'detail': 'Authentication credentials were not provided or are invalid.',
            'code': 'UNAUTHORIZED',
          },
        ),
        type: DioExceptionType.badResponse,
      );

      final failure = ProblemDetailsInterceptor.mapDioExceptionToFailure(dioError);

      expect(failure, isA<AuthFailure>());
      expect(failure.statusCode, equals(401));
      expect(failure.code, equals('UNAUTHORIZED'));
    });

    test('ProblemDetailsInterceptor translates connectionTimeout into NetworkFailure.timeout', () {
      final dioError = DioException(
        requestOptions: RequestOptions(
          path: '/api/v1/search/proximity',
          connectTimeout: const Duration(seconds: 10),
        ),
        type: DioExceptionType.connectionTimeout,
      );

      final failure = ProblemDetailsInterceptor.mapDioExceptionToFailure(dioError);

      expect(failure, isA<NetworkFailure>());
      expect(failure.code, equals('TIMEOUT'));
    });

    test('ProblemDetailsInterceptor translates connectionError into subterranean dead zone NetworkFailure', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/api/v1/access/validate-scan'),
        type: DioExceptionType.connectionError,
      );

      final failure = ProblemDetailsInterceptor.mapDioExceptionToFailure(dioError);

      expect(failure, isA<NetworkFailure>());
      final netFailure = failure as NetworkFailure;
      expect(netFailure.code, equals('CONNECTION_FAILED'));
      expect(netFailure.isSubterraneanDeadZone, isTrue);
    });

    test('ApiClient initializes with correct timeout configuration from EnvConfig', () {
      final client = ApiClient(storageService: storage, envConfig: devConfig);

      expect(client.dio.options.connectTimeout, equals(const Duration(seconds: 10)));
      expect(client.dio.options.receiveTimeout, equals(const Duration(seconds: 10)));
      expect(client.dio.options.sendTimeout, equals(const Duration(seconds: 10)));
      expect(client.dio.options.baseUrl, equals('http://10.0.2.2:8000'));
    });
  });
}
