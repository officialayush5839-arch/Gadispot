/// Environment configuration for Gadispot Mobile Client.
/// Supports development, staging, and production environments with typed timeouts and feature flags.

enum AppEnvironment {
  dev,
  staging,
  prod,
}

class EnvConfig {
  final AppEnvironment environment;
  final String baseUrl;
  final Duration connectTimeout;
  final Duration receiveTimeout;
  final Duration sendTimeout;
  final Map<String, bool> featureFlags;

  const EnvConfig({
    required this.environment,
    required this.baseUrl,
    this.connectTimeout = const Duration(seconds: 10),
    this.receiveTimeout = const Duration(seconds: 10),
    this.sendTimeout = const Duration(seconds: 10),
    this.featureFlags = const {},
  });

  bool get isDev => environment == AppEnvironment.dev;
  bool get isStaging => environment == AppEnvironment.staging;
  bool get isProd => environment == AppEnvironment.prod;

  bool isFeatureEnabled(String flagName) {
    return featureFlags[flagName] ?? false;
  }

  /// Safe local development defaults
  factory EnvConfig.dev({String? customBaseUrl}) {
    return EnvConfig(
      environment: AppEnvironment.dev,
      baseUrl: customBaseUrl ?? 'http://10.0.2.2:8000',
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      sendTimeout: const Duration(seconds: 10),
      featureFlags: const {
        'offlinePassCache': true,
        'biometricAuth': false,
        'verboseLogging': true,
        'mockSmsOtp': true,
      },
    );
  }

  /// Staging / QA testing environment
  factory EnvConfig.staging() {
    return const EnvConfig(
      environment: AppEnvironment.staging,
      baseUrl: 'https://staging-api.gadispot.in',
      connectTimeout: Duration(seconds: 10),
      receiveTimeout: Duration(seconds: 10),
      sendTimeout: Duration(seconds: 10),
      featureFlags: {
        'offlinePassCache': true,
        'biometricAuth': true,
        'verboseLogging': true,
        'mockSmsOtp': false,
      },
    );
  }

  /// Production environment — Bengaluru Pilot Baseline
  factory EnvConfig.prod() {
    return const EnvConfig(
      environment: AppEnvironment.prod,
      baseUrl: 'https://api.gadispot.in',
      connectTimeout: Duration(seconds: 10),
      receiveTimeout: Duration(seconds: 10),
      sendTimeout: Duration(seconds: 10),
      featureFlags: {
        'offlinePassCache': true,
        'biometricAuth': true,
        'verboseLogging': false,
        'mockSmsOtp': false,
      },
    );
  }

  static EnvConfig _current = EnvConfig.dev();

  static EnvConfig get current => _current;

  static void initialize(EnvConfig config) {
    _current = config;
  }
}
