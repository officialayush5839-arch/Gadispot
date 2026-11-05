import 'package:flutter/material.dart';
import '../../../core/routing/app_router.dart';
import 'search_view.dart';
import 'active_reservation_view.dart';
import 'bookings_view.dart';
import 'vehicles_view.dart';

/// Navigation shell for Driver users.
class DriverShell extends StatefulWidget {
  const DriverShell({super.key});

  @override
  State<DriverShell> createState() => _DriverShellState();
}

class _DriverShellState extends State<DriverShell> {
  int _currentIndex = 0;

  final List<Widget> _views = const [
    SearchView(),
    ActiveReservationView(),
    BookingsView(),
    VehiclesView(),
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
            icon: Icon(Icons.search_outlined),
            activeIcon: Icon(Icons.search),
            label: 'Search',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.qr_code_outlined),
            activeIcon: Icon(Icons.qr_code),
            label: 'Pass / Active',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.history_outlined),
            activeIcon: Icon(Icons.history),
            label: 'Bookings',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.directions_car_outlined),
            activeIcon: Icon(Icons.directions_car),
            label: 'Vehicles',
          ),
        ],
      ),
    );
  }
}
