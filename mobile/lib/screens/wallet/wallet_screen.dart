import 'package:flutter/material.dart';
import '../../services/api_service.dart';
import '../../utils/app_theme.dart';

class WalletScreen extends StatefulWidget {
  const WalletScreen({super.key});

  @override
  State<WalletScreen> createState() => _WalletScreenState();
}

class _WalletScreenState extends State<WalletScreen> {
  List<Map<String, dynamic>> _wallets = [];
  Map<String, dynamic>? _stats;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final wallets = await ApiService().getWallets();
      final stats = await ApiService().getStats();
      setState(() {
        _wallets = wallets.cast<Map<String, dynamic>>();
        _stats = stats;
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  Future<void> _confirmReset() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.card,
        title: const Text('Reset Wallet?'),
        content: const Text('This will reset your balance to \$10,000 and close all positions.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Reset', style: TextStyle(color: AppColors.red)),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await ApiService().resetWallet();
      _loadData();
    }
  }

  @override
  Widget build(BuildContext context) {
    final totalBalance = _wallets.fold<double>(
      0.0, (sum, w) => sum + ((w['balance'] as num).toDouble()),
    );

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Wallet'),
        actions: [
          TextButton(
            onPressed: _confirmReset,
            child: const Text('Reset', style: TextStyle(color: AppColors.red)),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : RefreshIndicator(
              onRefresh: _loadData,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    // Total balance card
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(24),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [AppColors.primary, Color(0xFF8B5CF6)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Column(
                        children: [
                          const Text('Total Portfolio Value', style: TextStyle(color: Colors.white70)),
                          const SizedBox(height: 8),
                          Text(
                            '\$${totalBalance.toStringAsFixed(2)}',
                            style: const TextStyle(
                              fontSize: 36, fontWeight: FontWeight.bold, color: Colors.white,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),

                    // Individual wallets
                    ..._wallets.map((w) {
                      final type = w['wallet_type'] as String;
                      final balance = (w['balance'] as num).toDouble();
                      final available = (w['available_balance'] as num).toDouble();
                      return Card(
                        margin: const EdgeInsets.only(bottom: 12),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Row(
                            children: [
                              Container(
                                width: 44,
                                height: 44,
                                decoration: BoxDecoration(
                                  color: (type == 'spot' ? AppColors.primary : AppColors.yellow).withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Icon(
                                  type == 'spot' ? Icons.account_balance : Icons.trending_up,
                                  color: type == 'spot' ? AppColors.primary : AppColors.yellow,
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      type[0].toUpperCase() + type.substring(1),
                                      style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
                                    ),
                                    Text(
                                      'Available: \$${available.toStringAsFixed(2)}',
                                      style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
                                    ),
                                  ],
                                ),
                              ),
                              Text(
                                '\$${balance.toStringAsFixed(2)}',
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                              ),
                            ],
                          ),
                        ),
                      );
                    }),

                    const SizedBox(height: 20),

                    // Stats
                    if (_stats != null) ...[
                      const Text(
                        'Trading Statistics',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                      ),
                      const SizedBox(height: 12),
                      _buildStatGrid(),
                    ],
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildStatGrid() {
    final stats = _stats!;
    final items = [
      ('Total Trades', '${stats['total_trades']}', AppColors.primary),
      ('Win Rate', '${(stats['win_rate'] as num).toStringAsFixed(1)}%', AppColors.green),
      ('Total PnL', '\$${(stats['total_pnl'] as num).toStringAsFixed(2)}',
          (stats['total_pnl'] as num) >= 0 ? AppColors.green : AppColors.red),
      ('Best Trade', '\$${(stats['best_trade'] as num).toStringAsFixed(2)}', AppColors.green),
    ];

    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.6,
      children: items.map((item) {
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(item.$1, style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                const SizedBox(height: 4),
                Text(item.$2, style: TextStyle(fontWeight: FontWeight.bold, color: item.$3, fontSize: 18)),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }
}
