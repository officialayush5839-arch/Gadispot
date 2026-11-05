import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../core/constants/app_constants.dart';
import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_theme.dart';

/// Clean, monochromatic phone number authentication entry point.
class LoginView extends StatefulWidget {
  const LoginView({super.key});

  @override
  State<LoginView> createState() => _LoginViewState();
}

class _LoginViewState extends State<LoginView> {
  final _phoneController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _isLoading = false;

  @override
  void dispose() {
    _phoneController.dispose();
    super.dispose();
  }

  void _submitPhoneNumber() {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() => _isLoading = true);
    final rawNumber = _phoneController.text.trim();
    final formattedPhone = '+91$rawNumber';

    // Simulate OTP dispatch and transition to OTP screen
    Navigator.of(context).pushNamed(
      AppRouter.otp,
      arguments: formattedPhone,
    ).then((_) {
      if (mounted) setState(() => _isLoading = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primaryTextColor = isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary;
    final secondaryTextColor = isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary;

    return Scaffold(
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
                    // Brand Identity
                    Text(
                      AppConstants.appName.toUpperCase(),
                      style: TextStyle(
                        color: primaryTextColor,
                        fontSize: 28,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(height: AppTheme.spacing8),
                    Text(
                      'High-concurrency urban parking marketplace.\nEnter your phone number to sign in or register.',
                      style: TextStyle(
                        color: secondaryTextColor,
                        fontSize: 14,
                        height: 1.4,
                      ),
                    ),
                    const SizedBox(height: AppTheme.spacing32),

                    // Phone Input Field with Indian +91 Prefix
                    TextFormField(
                      controller: _phoneController,
                      keyboardType: TextInputType.phone,
                      maxLength: 10,
                      inputFormatters: [
                        FilteringTextInputFormatter.digitsOnly,
                      ],
                      decoration: InputDecoration(
                        labelText: 'Phone Number',
                        hintText: '9876543210',
                        counterText: '',
                        prefixIcon: Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: AppTheme.spacing12,
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                '+91',
                                style: TextStyle(
                                  color: primaryTextColor,
                                  fontWeight: FontWeight.w600,
                                  fontSize: 14,
                                ),
                              ),
                              const SizedBox(width: AppTheme.spacing8),
                              Container(
                                width: 1,
                                height: 18,
                                color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
                              ),
                            ],
                          ),
                        ),
                      ),
                      validator: (val) {
                        if (val == null || val.trim().length != 10) {
                          return 'Enter a valid 10-digit Indian mobile number';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: AppTheme.spacing20),

                    // Action Button
                    ElevatedButton(
                      onPressed: _isLoading ? null : _submitPhoneNumber,
                      child: _isLoading
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('CONTINUE WITH OTP'),
                    ),
                    const SizedBox(height: AppTheme.spacing24),

                    // Legal / Privacy note
                    Text(
                      'By continuing, you agree to Gadispot Terms of Service and DPDPA-compliant 7-day gate photo minimization.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: isDark ? AppTheme.darkTextMuted : AppTheme.lightTextMuted,
                        fontSize: 11,
                        height: 1.3,
                      ),
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
