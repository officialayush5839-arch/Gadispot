import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Top banner alerting users to cellular dead-zone / offline status in subterranean parking areas.
/// Confirms that cached parking passes remain active and valid for guard admission.
class OfflineBanner extends StatelessWidget {
  final bool isOffline;
  final String? customMessage;
  final VoidCallback? onRetry;

  const OfflineBanner({
    super.key,
    required this.isOffline,
    this.customMessage,
    this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    if (!isOffline) {
      return const SizedBox.shrink();
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: AppTheme.spacing16,
        vertical: AppTheme.spacing8,
      ),
      decoration: const BoxDecoration(
        color: AppTheme.offlineBannerBg,
        border: Border(
          bottom: BorderSide(
            color: AppTheme.offlineBannerBorder,
            width: AppTheme.borderWidth,
          ),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: AppTheme.semanticWarning,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          const SizedBox(width: AppTheme.spacing8),
          Expanded(
            child: Text(
              customMessage ??
                  'Subterranean Dead Zone — Showing cached pass. Valid for gate admission.',
              style: const TextStyle(
                color: AppTheme.offlineBannerText,
                fontSize: 12,
                fontWeight: FontWeight.w500,
                letterSpacing: -0.2,
              ),
            ),
          ),
          if (onRetry != null) ...[
            const SizedBox(width: AppTheme.spacing8),
            GestureDetector(
              onTap: onRetry,
              child: const Text(
                'RETRY',
                style: TextStyle(
                  color: AppTheme.darkTextPrimary,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.5,
                  decoration: TextDecoration.underline,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
