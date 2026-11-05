import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_theme.dart';

/// OTP Verification View with 60-second resend cooldown and role viewport selection.
class OtpView extends StatefulWidget {
  final String phoneNumber;

  const OtpView({
    super.key,
    required this.phoneNumber,
  });

  @override
  State<OtpView> createState() => _OtpViewState();
}

class _OtpViewState extends State<OtpView> {
  final _otpController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  UserRole _selectedRole = UserRole.driver;
  int _resendCooldown = 60;
  Timer? _cooldownTimer;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _startCooldownTimer();
  }

  @override
  void dispose() {
    _cooldownTimer?.cancel();
    _otpController.dispose();
    super.dispose();
  }

  void _startCooldownTimer() {
    _resendCooldown = 60;
    _cooldownTimer?.cancel();
    _cooldownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      if (_resendCooldown > 0) {
        setState(() => _resendCooldown--);
      } else {
        timer.cancel();
      }
    });
  }

  void _verifyOtp() {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() => _isLoading = true);

    // Resolve initial route based on selected role
    final targetRoute = AppRouter.resolveInitialRoute(_selectedRole);
    Navigator.of(context).pushNamedAndRemoveUntil(targetRoute, (route) => false);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primaryTextColor = isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary;
    final secondaryTextColor = isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Verify Code'),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppTheme.spacing24),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'Enter 6-digit OTP',
                      style: TextStyle(
                        color: primaryTextColor,
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const SizedBox(height: AppTheme.spacing8),
                    Text(
                      'A verification code has been dispatched to ${widget.phoneNumber}.',
                      style: TextStyle(
                        color: secondaryTextColor,
                        fontSize: 14,
                        height: 1.4,
                      ),
                    ),
                    const SizedBox(height: AppTheme.spacing24),

                    // OTP Input
                    TextFormField(
                      controller: _otpController,
                      keyboardType: TextInputType.number,
                      textAlign: TextAlign.center,
                      maxLength: 6,
                      style: const TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 8,
                      ),
                      inputFormatters: [
                        FilteringTextInputFormatter.digitsOnly,
                      ],
                      decoration: const InputDecoration(
                        hintText: '000000',
                        counterText: '',
                      ),
                      validator: (val) {
                        if (val == null || val.trim().length != 6) {
                          return 'Please enter 6-digit verification code';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: AppTheme.spacing20),

                    // Role Viewport Selector (Driver, Owner, Guard, Operations)
                    Container(
                      padding: const EdgeInsets.all(AppTheme.spacing12),
                      decoration: BoxDecoration(
                        color: isDark ? AppTheme.darkSurface : AppTheme.lightSurface,
                        borderRadius: BorderRadius.circular(AppTheme.radiusSm),
                        border: Border.all(
                          color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
                          width: AppTheme.borderWidth,
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'SELECT ACTIVE ROLE SHELL',
                            style: TextStyle(
                              color: isDark ? AppTheme.darkTextMuted : AppTheme.lightTextMuted,
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 0.5,
                            ),
                          ),
                          const SizedBox(height: AppTheme.spacing8),
                          DropdownButtonFormField<UserRole>(
                            value: _selectedRole,
                            decoration: const InputDecoration(
                              contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            ),
                            items: const [
                              DropdownMenuItem(
                                value: UserRole.driver,
                                child: Text('Driver (Search & Book Parking)'),
                              ),
                              DropdownMenuItem(
                                value: UserRole.owner,
                                child: Text('Space Owner (Bays & Schedules)'),
                              ),
                              DropdownMenuItem(
                                value: UserRole.guard,
                                child: Text('Security Guard (Gate Pass Scanner)'),
                              ),
                              DropdownMenuItem(
                                value: UserRole.operations,
                                child: Text('Operations (NOC & Approvals)'),
                              ),
                            ],
                            onChanged: (role) {
                              if (role != null) {
                                setState(() => _selectedRole = role);
                              }
                            },
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: AppTheme.spacing20),

                    // Verify Button
                    ElevatedButton(
                      onPressed: _isLoading ? null : _verifyOtp,
                      child: _isLoading
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('VERIFY & ACCESS'),
                    ),
                    const SizedBox(height: AppTheme.spacing16),

                    // Resend Timer Row
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          _resendCooldown > 0
                              ? 'Resend OTP in ${_resendCooldown}s'
                              : 'Did not receive code? ',
                          style: TextStyle(
                            color: secondaryTextColor,
                            fontSize: 13,
                          ),
                        ),
                        if (_resendCooldown == 0)
                          GestureDetector(
                            onTap: _startCooldownTimer,
                            child: Text(
                              'RESEND NOW',
                              style: TextStyle(
                                color: primaryTextColor,
                                fontWeight: FontWeight.w700,
                                fontSize: 13,
                                decoration: TextDecoration.underline,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
