import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gadispot_mobile/core/theme/app_theme.dart';

void main() {
  group('AppTheme Anti-Slop & Token Verification Tests', () {
    test('Dark theme enforces monochromatic palette and dark background', () {
      final theme = AppTheme.darkTheme;
      expect(theme.brightness, equals(Brightness.dark));
      expect(theme.scaffoldBackgroundColor, equals(const Color(0xFF0A0A0A)));
      expect(theme.cardColor, equals(const Color(0xFF141414)));
      expect(theme.dividerColor, equals(const Color(0xFF262626)));
    });

    test('Light theme enforces crisp neutral palette and high contrast background', () {
      final theme = AppTheme.lightTheme;
      expect(theme.brightness, equals(Brightness.light));
      expect(theme.scaffoldBackgroundColor, equals(const Color(0xFFF9FAFB)));
      expect(theme.cardColor, equals(const Color(0xFFFFFFFF)));
      expect(theme.dividerColor, equals(const Color(0xFFE5E7EB)));
    });

    test('Theme enforces hair-thin 1px border tokens', () {
      expect(AppTheme.borderWidth, equals(1.0));
    });

    test('Spacing tokens strictly follow 4px/8px modular grid', () {
      const tokens = [
        AppTheme.spacing4,
        AppTheme.spacing8,
        AppTheme.spacing12,
        AppTheme.spacing16,
        AppTheme.spacing20,
        AppTheme.spacing24,
        AppTheme.spacing32,
        AppTheme.spacing40,
        AppTheme.spacing48,
        AppTheme.spacing64,
      ];

      for (final token in tokens) {
        expect(token % 4.0, equals(0.0), reason: 'Spacing token $token must be divisible by 4px');
      }
    });

    test('Border radii are architectural and restrained (max 8px, zero oversized pills)', () {
      expect(AppTheme.radiusNone, equals(0.0));
      expect(AppTheme.radiusXs, equals(2.0));
      expect(AppTheme.radiusSm, equals(4.0));
      expect(AppTheme.radiusMd, equals(8.0));
      expect(AppTheme.radiusMd <= 8.0, isTrue);
    });

    test('QR container tokens guarantee high contrast for subterranean scanning', () {
      expect(AppTheme.qrContainerBackground, equals(const Color(0xFFFFFFFF)));
      expect(AppTheme.qrForeground, equals(const Color(0xFF000000)));
      expect(AppTheme.qrBorder, equals(const Color(0xFFE5E7EB)));
    });

    test('Offline subterranean banner tokens provide high legibility', () {
      expect(AppTheme.offlineBannerBg, equals(const Color(0xFF1C1917)));
      expect(AppTheme.offlineBannerText, equals(const Color(0xFFF5F5F4)));
      expect(AppTheme.offlineBannerBorder, equals(const Color(0xFF44403C)));
    });
  });
}
