import 'package:flutter/material.dart';
import '../../../core/constants/app_constants.dart';
import '../../../core/theme/app_theme.dart';

/// Vehicle management view with Indian license plate regex validation.
class VehiclesView extends StatefulWidget {
  const VehiclesView({super.key});

  @override
  State<VehiclesView> createState() => _VehiclesViewState();
}

class _VehiclesViewState extends State<VehiclesView> {
  final List<Map<String, dynamic>> _vehicles = [
    {
      'plate': 'KA01MJ4092',
      'make': 'Hyundai Creta',
      'category': 'SUV / Compact Crossover',
      'dimensions': '4.30m × 1.79m × 1.63m',
      'isDefault': true,
      'isEv': false,
    },
    {
      'plate': 'KA05NB1188',
      'make': 'Tata Nexon EV',
      'category': 'Compact SUV (Electric)',
      'dimensions': '3.99m × 1.81m × 1.60m',
      'isDefault': false,
      'isEv': true,
    },
  ];

  void _showAddVehicleModal() {
    final plateController = TextEditingController();
    final makeController = TextEditingController();
    final formKey = GlobalKey<FormState>();
    bool isEv = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusMd)),
      ),
      builder: (ctx) {
        final isDark = Theme.of(ctx).brightness == Brightness.dark;
        return StatefulBuilder(
          builder: (ctx, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: AppTheme.spacing24,
                right: AppTheme.spacing24,
                top: AppTheme.spacing24,
                bottom: MediaQuery.of(ctx).viewInsets.bottom + AppTheme.spacing24,
              ),
              child: Form(
                key: formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'Register Vehicle Profile',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
                      ),
                    ),
                    const SizedBox(height: AppTheme.spacing8),
                    Text(
                      'Dimensions are used to ensure clearance compatibility with parking bays.',
                      style: TextStyle(
                        fontSize: 12,
                        color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
                      ),
                    ),
                    const SizedBox(height: AppTheme.spacing20),
                    TextFormField(
                      controller: plateController,
                      textCapitalization: TextCapitalization.characters,
                      decoration: const InputDecoration(
                        labelText: 'Indian Registration Plate',
                        hintText: 'KA01AB1234',
                      ),
                      validator: (val) {
                        if (val == null || !AppConstants.indianPlateRegex.hasMatch(val.trim())) {
                          return 'Enter valid Indian plate (e.g., KA01AB1234)';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: AppTheme.spacing12),
                    TextFormField(
                      controller: makeController,
                      decoration: const InputDecoration(
                        labelText: 'Make & Model',
                        hintText: 'e.g. Honda City, Maruti Swift',
                      ),
                      validator: (val) {
                        if (val == null || val.trim().isEmpty) {
                          return 'Please enter vehicle make/model';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: AppTheme.spacing12),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Electric Vehicle (EV)', style: TextStyle(fontSize: 14)),
                      value: isEv,
                      onChanged: (val) => setModalState(() => isEv = val),
                    ),
                    const SizedBox(height: AppTheme.spacing20),
                    ElevatedButton(
                      onPressed: () {
                        if (formKey.currentState!.validate()) {
                          setState(() {
                            _vehicles.add({
                              'plate': plateController.text.trim().toUpperCase(),
                              'make': makeController.text.trim(),
                              'category': isEv ? 'Electric Vehicle' : 'Internal Combustion',
                              'dimensions': '4.20m × 1.76m × 1.50m',
                              'isDefault': false,
                              'isEv': isEv,
                            });
                          });
                          Navigator.pop(ctx);
                        }
                      },
                      child: const Text('SAVE VEHICLE PROFILE'),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Registered Vehicles'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: _showAddVehicleModal,
          ),
        ],
      ),
      body: SafeArea(
        child: ListView.separated(
          padding: const EdgeInsets.all(AppTheme.spacing16),
          itemCount: _vehicles.length,
          separatorBuilder: (_, __) => const SizedBox(height: AppTheme.spacing12),
          itemBuilder: (context, index) {
            final v = _vehicles[index];
            return Container(
              padding: const EdgeInsets.all(AppTheme.spacing16),
              decoration: BoxDecoration(
                color: isDark ? AppTheme.darkSurface : AppTheme.lightSurface,
                borderRadius: BorderRadius.circular(AppTheme.radiusMd),
                border: Border.all(
                  color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
                  width: AppTheme.borderWidth,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppTheme.spacing8,
                          vertical: AppTheme.spacing4,
                        ),
                        decoration: BoxDecoration(
                          color: isDark ? AppTheme.darkSurfaceElevated : AppTheme.lightSurfaceElevated,
                          borderRadius: BorderRadius.circular(AppTheme.radiusSm),
                          border: Border.all(
                            color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
                            width: AppTheme.borderWidth,
                          ),
                        ),
                        child: Text(
                          v['plate'] as String,
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.5,
                            color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
                          ),
                        ),
                      ),
                      if (v['isDefault'] == true)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0xFFDCFCE7),
                            borderRadius: BorderRadius.circular(AppTheme.radiusSm),
                          ),
                          child: const Text(
                            'DEFAULT',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF166534),
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: AppTheme.spacing12),
                  Text(
                    v['make'] as String,
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: isDark ? AppTheme.darkTextPrimary : AppTheme.lightTextPrimary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${v['category']} • Clearance: ${v['dimensions']}',
                    style: TextStyle(
                      fontSize: 12,
                      color: isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary,
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}
