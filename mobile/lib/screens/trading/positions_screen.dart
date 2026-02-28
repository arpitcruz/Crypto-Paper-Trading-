import 'package:flutter/material.dart';
import '../../services/api_service.dart';
import '../../services/websocket_service.dart';
import '../../utils/app_theme.dart';

class PositionsScreen extends StatefulWidget {
  const PositionsScreen({super.key});

  @override
  State<PositionsScreen> createState() => _PositionsScreenState();
}

class _PositionsScreenState extends State<PositionsScreen> {
  List<Map<String, dynamic>> _positions = [];
  final Map<String, Map<String, dynamic>> _pnlUpdates = {};
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadPositions();
    WebSocketService().userStream.listen((msg) {
      if (msg['type'] == 'pnl_update' && mounted) {
        final updates = msg['positions'] as List;
        setState(() {
          for (final u in updates) {
            _pnlUpdates[u['position_id']] = Map<String, dynamic>.from(u);
          }
        });
      }
    });
  }

  Future<void> _loadPositions() async {
    try {
      final data = await ApiService().getPositions();
      setState(() {
        _positions = data.cast<Map<String, dynamic>>();
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  Future<void> _closePosition(String positionId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.card,
        title: const Text('Close Position?'),
        content: const Text('This will close the position at the current market price.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Close', style: TextStyle(color: AppColors.red)),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await ApiService().closePosition(positionId);
      _loadPositions();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Positions'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadPositions),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : _positions.isEmpty
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.trending_flat, size: 64, color: AppColors.textMuted),
                  SizedBox(height: 16),
                  Text('No open positions', style: TextStyle(color: AppColors.textSecondary)),
                ],
              ),
            )
          : RefreshIndicator(
              onRefresh: _loadPositions,
              child: ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: _positions.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder: (_, i) {
                  final pos = _positions[i];
                  final id = pos['id'] as String;
                  final update = _pnlUpdates[id];
                  final pnl = update?['unrealized_pnl'] ?? pos['unrealized_pnl'] ?? 0.0;
                  final roe = update?['roe_percent'] ?? 0.0;
                  final currentPrice = update?['current_price'] ?? pos['current_price'];
                  final isLong = pos['side'] == 'long';
                  final pnlPositive = (pnl as num).toDouble() >= 0;

                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: (isLong ? AppColors.green : AppColors.red).withOpacity(0.15),
                                          borderRadius: BorderRadius.circular(4),
                                        ),
                                        child: Text(
                                          isLong ? 'LONG' : 'SHORT',
                                          style: TextStyle(
                                            color: isLong ? AppColors.green : AppColors.red,
                                            fontSize: 11, fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Text(
                                        pos['symbol'] as String,
                                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                                      ),
                                      const SizedBox(width: 6),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: AppColors.yellow.withOpacity(0.15),
                                          borderRadius: BorderRadius.circular(4),
                                        ),
                                        child: Text(
                                          '${pos['leverage']}x',
                                          style: const TextStyle(color: AppColors.yellow, fontSize: 11),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'Entry: \$${(pos['entry_price'] as num).toStringAsFixed(4)}',
                                    style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
                                  ),
                                ],
                              ),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  Text(
                                    '${pnlPositive ? '+' : ''}\$${(pnl as num).toStringAsFixed(2)}',
                                    style: TextStyle(
                                      color: pnlPositive ? AppColors.green : AppColors.red,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 18,
                                    ),
                                  ),
                                  Text(
                                    '${pnlPositive ? '+' : ''}${roe.toStringAsFixed(2)}% ROE',
                                    style: TextStyle(
                                      color: pnlPositive ? AppColors.green : AppColors.red,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                'Mark: \$${currentPrice?.toString() ?? '—'}',
                                style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
                              ),
                              Text(
                                'Liq: \$${(pos['liquidation_price'] as num?)?.toStringAsFixed(2) ?? '—'}',
                                style: const TextStyle(color: AppColors.red, fontSize: 13),
                              ),
                              TextButton(
                                onPressed: () => _closePosition(id),
                                style: TextButton.styleFrom(
                                  foregroundColor: AppColors.red,
                                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                ),
                                child: const Text('Close'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
    );
  }
}
