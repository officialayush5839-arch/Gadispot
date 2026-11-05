import 'dart:ui';
import 'package:flutter/material.dart';
import 'core/config/env.dart';
import 'core/constants/app_constants.dart';
import 'core/routing/app_router.dart';
import 'core/theme/app_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize environment configuration with safe local development defaults
  EnvConfig.initialize(EnvConfig.dev());

  // Set up global error boundaries
  FlutterError.onError = (FlutterErrorDetails details) {
    FlutterError.presentError(details);
    // In production, dispatch to secure crash reporting service
    debugPrint('[FLUTTER ERROR] ${details.exceptionAsString()}');
  };

  PlatformDispatcher.instance.onError = (Object error, StackTrace stack) {
    debugPrint('[PLATFORM ASYNC ERROR] $error\n$stack');
    return true;
  };

  runApp(const GadispotApp());
}

/// Root Application Widget for Gadispot Mobile Client.
class GadispotApp extends StatelessWidget {
  const GadispotApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppConstants.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      initialRoute: AppRouter.root,
      onGenerateRoute: AppRouter.onGenerateRoute,
    );
  }
}
