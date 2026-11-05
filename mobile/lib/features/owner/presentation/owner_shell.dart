import 'package:flutter/material.dart';
import 'property_overview_view.dart';
import 'bay_management_view.dart';
import 'earnings_view.dart';

/// Navigation shell for Space Owners.
class OwnerShell extends StatefulWidget {
  const OwnerShell({super.key});

  @override
  State<OwnerShell> createState() => _OwnerShellState();
}

class _OwnerShellState extends State<OwnerShell> {
  int _currentIndex = 0;

  final List<Widget> _views = const [
    PropertyOverviewView(),
    BayManagementView(),
    EarningsView(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _views,
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.apartment_outlined),
            activeIcon: Icon(Icons.apartment),
            label: 'Overview',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.local_parking_outlined),
            activeIcon: Icon(Icons.local_parking),
            label: 'Bays',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.account_balance_wallet_outlined),
            activeIcon: Icon(Icons.account_balance_wallet),
            label: 'Earnings',
          ),
        ],
      ),
    );
  }
}
