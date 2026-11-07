import 'package:flutter/material.dart';
import '../routing/app_router.dart';
import '../theme/app_theme.dart';

/// Minimalist, monochromatic segmented role switcher allowing dual-role users
/// (Driver and Space Owner) to toggle active viewports dynamically without re-authenticating.
class RoleSwitcher extends StatelessWidget {
  final UserRole activeRole;
  final List<UserRole> allowedRoles;
  final ValueChanged<UserRole> onRoleChanged;

  const RoleSwitcher({
    super.key,
    required this.activeRole,
    required this.allowedRoles,
    required this.onRoleChanged,
  });

  @override
  Widget build(BuildContext context) {
    // Only show switcher if user possesses multiple switchable roles (Driver + Owner)
    final canSwitch = allowedRoles.contains(UserRole.driver) &&
        (allowedRoles.contains(UserRole.owner) || allowedRoles.contains(UserRole.operations));
    if (!canSwitch) {
      return const SizedBox.shrink();
    }

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final borderColor = isDark ? AppTheme.darkBorder : AppTheme.lightBorder;
    final surfaceColor = isDark ? AppTheme.darkSurface : AppTheme.lightSurface;
    final activeColor = isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary;
    final inactiveColor = isDark ? AppTheme.darkTextMuted : AppTheme.lightTextMuted;

    return Container(
      height: 36,
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        color: surfaceColor,
        borderRadius: BorderRadius.circular(AppTheme.radiusSm),
        border: Border.all(color: borderColor, width: AppTheme.borderWidth),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildPill(
            label: 'DRIVER',
            role: UserRole.driver,
            isSelected: activeRole == UserRole.driver,
            activeColor: activeColor,
            inactiveColor: inactiveColor,
            isDark: isDark,
          ),
          const SizedBox(width: 4),
          _buildPill(
            label: 'SPACE OWNER',
            role: UserRole.owner,
            isSelected: activeRole == UserRole.owner,
            activeColor: activeColor,
            inactiveColor: inactiveColor,
            isDark: isDark,
          ),
        ],
      ),
    );
  }

  Widget _buildPill({
    required String label,
    required UserRole role,
    required bool isSelected,
    required Color activeColor,
    required Color inactiveColor,
    required bool isDark,
  }) {
    return GestureDetector(
      onTap: () {
        if (!isSelected) {
          onRoleChanged(role);
        }
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        curve: Curves.easeInOut,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected
              ? (isDark ? const Color(0xFF262626) : const Color(0xFFE5E5E5))
              : Colors.transparent,
          borderRadius: BorderRadius.circular(AppTheme.radiusSm - 2),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? activeColor : inactiveColor,
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
            letterSpacing: 0.5,
          ),
        ),
      ),
    );
  }
}
