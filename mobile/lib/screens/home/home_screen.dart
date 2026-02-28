import 'package:flutter/material.dart';
import '../../utils/app_theme.dart';
import '../market/market_screen.dart';
import '../trading/trading_screen.dart';
import '../trading/positions_screen.dart';
import '../wallet/wallet_screen.dart';
import '../profile/profile_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  final _screens = const [
    MarketScreen(),
    TradingScreen(),
    PositionsScreen(),
    WalletScreen(),
    ProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _currentIndex, children: _screens),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: AppColors.border)),
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (i) => setState(() => _currentIndex = i),
          items: const [
            BottomNavigationBarItem(icon: Icon(Icons.bar_chart), label: 'Markets'),
            BottomNavigationBarItem(icon: Icon(Icons.swap_horiz), label: 'Trade'),
            BottomNavigationBarItem(icon: Icon(Icons.trending_up), label: 'Positions'),
            BottomNavigationBarItem(icon: Icon(Icons.account_balance_wallet), label: 'Wallet'),
            BottomNavigationBarItem(icon: Icon(Icons.person_outline), label: 'Profile'),
          ],
        ),
      ),
    );
  }
}
