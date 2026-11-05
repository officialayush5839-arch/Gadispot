import 'package:flutter/material.dart';
import 'approvals_view.dart';
import 'manual_review_view.dart';

/// Navigation shell for Operations and Administration.
class OpsShell extends StatefulWidget {
  const OpsShell({super.key});

  @override
  State<OpsShell> createState() => _OpsShellState();
}

class _OpsShellState extends State<OpsShell> {
  int _currentIndex = 0;

  final List<Widget> _views = const [
    ApprovalsView(),
    ManualReviewView(),
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
            icon: Icon(Icons.verified_outlined),
            activeIcon: Icon(Icons.verified),
            label: 'Property Approvals',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.gavel_outlined),
            activeIcon: Icon(Icons.gavel),
            label: 'Manual Reviews',
          ),
        ],
      ),
    );
  }
}
