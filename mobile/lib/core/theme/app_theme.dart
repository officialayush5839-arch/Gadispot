import 'package:flutter/material.dart';

/// Monochromatic, Anti-Slop Design System for Gadispot Mobile Application.
/// Strictly enforces:
/// - Pure monochromatic base structures (Deep neutral #0A0A0A dark, Crisp #FFFFFF / #F9FAFB light)
/// - Hair-thin 1px borders across all card and container surfaces
/// - Strict 4px/8px spacing grid tokens
/// - Restrained radii (4px/8px max, zero bubbly pills or oversized card radii)
/// - Zero AI-slop: banned purple/violet radial background glows, zero heavy frosted glass,
///   and zero emojis as icons.
class AppTheme {
  AppTheme._();

  // Spacing Tokens (Strict 4px/8px Grid)
  static const double spacing4 = 4.0;
  static const double spacing8 = 8.0;
  static const double spacing12 = 12.0;
  static const double spacing16 = 16.0;
  static const double spacing20 = 20.0;
  static const double spacing24 = 24.0;
  static const double spacing32 = 32.0;
  static const double spacing40 = 40.0;
  static const double spacing48 = 48.0;
  static const double spacing64 = 64.0;

  // Border Radii (Restrained & Architectural)
  static const double radiusNone = 0.0;
  static const double radiusXs = 2.0;
  static const double radiusSm = 4.0;
  static const double radiusMd = 8.0;

  // Border Widths
  static const double borderWidth = 1.0;

  // Dark Palette (Deep Neutral Monochromatic)
  static const Color darkBackground = Color(0xFF0A0A0A);
  static const Color darkSurface = Color(0xFF141414);
  static const Color darkSurfaceElevated = Color(0xFF1E1E1E);
  static const Color darkBorder = Color(0xFF262626);
  static const Color darkBorderStrong = Color(0xFF404040);
  static const Color darkTextPrimary = Color(0xFFFFFFFF);
  static const Color darkTextSecondary = Color(0xFFA3A3A3);
  static const Color darkTextMuted = Color(0xFF737373);

  // Light Palette (Crisp High-Contrast Neutral)
  static const Color lightBackground = Color(0xFFF9FAFB);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightSurfaceElevated = Color(0xFFF3F4F6);
  static const Color lightBorder = Color(0xFFE5E7EB);
  static const Color lightBorderStrong = Color(0xFFD1D5DB);
  static const Color lightTextPrimary = Color(0xFF111827);
  static const Color lightTextSecondary = Color(0xFF4B5563);
  static const Color lightTextMuted = Color(0xFF9CA3AF);

  // Functional Semantic Accents (High Contrast, Non-Slop)
  static const Color semanticError = Color(0xFFDC2626);
  static const Color semanticSuccess = Color(0xFF16A34A);
  static const Color semanticWarning = Color(0xFFD97706);
  static const Color semanticInfo = Color(0xFF2563EB);

  // QR Display High-Contrast Tokens
  static const Color qrContainerBackground = Color(0xFFFFFFFF);
  static const Color qrForeground = Color(0xFF000000);
  static const Color qrBorder = Color(0xFFE5E7EB);

  // Offline / Subterranean Dead Zone Banner Tokens
  static const Color offlineBannerBg = Color(0xFF1C1917);
  static const Color offlineBannerBorder = Color(0xFF44403C);
  static const Color offlineBannerText = Color(0xFFF5F5F4);

  /// Dark ThemeData definition
  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: darkBackground,
      primaryColor: darkTextPrimary,
      canvasColor: darkBackground,
      cardColor: darkSurface,
      dividerColor: darkBorder,
      colorScheme: const ColorScheme.dark(
        surface: darkSurface,
        primary: darkTextPrimary,
        secondary: darkTextSecondary,
        error: semanticError,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: darkBackground,
        foregroundColor: darkTextPrimary,
        elevation: 0,
        centerTitle: false,
        shape: Border(
          bottom: BorderSide(color: darkBorder, width: borderWidth),
        ),
      ),
      cardTheme: CardTheme(
        color: darkSurface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusMd),
          side: const BorderSide(color: darkBorder, width: borderWidth),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: darkTextPrimary,
          foregroundColor: darkBackground,
          elevation: 0,
          textStyle: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.2,
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: spacing16,
            vertical: spacing12,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radiusSm),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: darkTextPrimary,
          side: const BorderSide(color: darkBorder, width: borderWidth),
          padding: const EdgeInsets.symmetric(
            horizontal: spacing16,
            vertical: spacing12,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radiusSm),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: darkSurface,
        contentPadding: const EdgeInsets.all(spacing12),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: const BorderSide(color: darkBorder, width: borderWidth),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: const BorderSide(color: darkBorder, width: borderWidth),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: const BorderSide(color: darkTextPrimary, width: borderWidth),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: const BorderSide(color: semanticError, width: borderWidth),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: darkSurface,
        selectedItemColor: darkTextPrimary,
        unselectedItemColor: darkTextMuted,
        elevation: 0,
        type: BottomNavigationBarType.fixed,
      ),
    );
  }

  /// Light ThemeData definition
  static ThemeData get lightTheme {
    return ThemeData(
      brightness: Brightness.light,
      scaffoldBackgroundColor: lightBackground,
      primaryColor: lightTextPrimary,
      canvasColor: lightBackground,
      cardColor: lightSurface,
      dividerColor: lightBorder,
      colorScheme: const ColorScheme.light(
        surface: lightSurface,
        primary: lightTextPrimary,
        secondary: lightTextSecondary,
        error: semanticError,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: lightSurface,
        foregroundColor: lightTextPrimary,
        elevation: 0,
        centerTitle: false,
        shape: Border(
          bottom: BorderSide(color: lightBorder, width: borderWidth),
        ),
      ),
      cardTheme: CardTheme(
        color: lightSurface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusMd),
          side: const BorderSide(color: lightBorder, width: borderWidth),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: lightTextPrimary,
          foregroundColor: lightSurface,
          elevation: 0,
          textStyle: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.2,
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: spacing16,
            vertical: spacing12,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radiusSm),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: lightTextPrimary,
          side: const BorderSide(color: lightBorder, width: borderWidth),
          padding: const EdgeInsets.symmetric(
            horizontal: spacing16,
            vertical: spacing12,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radiusSm),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: lightSurface,
        contentPadding: const EdgeInsets.all(spacing12),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: const BorderSide(color: lightBorder, width: borderWidth),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: const BorderSide(color: lightBorder, width: borderWidth),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: const BorderSide(color: lightTextPrimary, width: borderWidth),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: const BorderSide(color: semanticError, width: borderWidth),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: lightSurface,
        selectedItemColor: lightTextPrimary,
        unselectedItemColor: lightTextMuted,
        elevation: 0,
        type: BottomNavigationBarType.fixed,
      ),
    );
  }
}
