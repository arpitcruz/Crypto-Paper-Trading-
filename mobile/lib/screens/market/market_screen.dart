import 'package:flutter/material.dart';
import '../../services/api_service.dart';
import '../../services/websocket_service.dart';
import '../../utils/app_theme.dart';
import '../trading/trading_screen.dart';

class MarketScreen extends StatefulWidget {
  const MarketScreen({super.key});

  @override
  State<MarketScreen> createState() => _MarketScreenState();
}

class _MarketScreenState extends State<MarketScreen> {
  List<Map<String, dynamic>> _tickers = [];
  final Map<String, double> _livePrices = {};
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadTickers();
    _listenWs();
  }

  Future<void> _loadTickers() async {
    try {
      final data = await ApiService().getTickers();
      setState(() {
        _tickers = data.cast<Map<String, dynamic>>();
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  void _listenWs() {
    WebSocketService().priceStream.listen((msg) {
      if (msg['type'] == 'ticker' && mounted) {
        setState(() {
          _livePrices[msg['symbol'] as String] = (msg['price'] as num).toDouble();
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Markets'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: () {},
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : RefreshIndicator(
              onRefresh: _loadTickers,
              child: ListView.separated(
                itemCount: _tickers.length,
                separatorBuilder: (_, __) => const Divider(color: AppColors.border, height: 1),
                itemBuilder: (_, i) {
                  final t = _tickers[i];
                  final symbol = t['symbol'] as String;
                  final livePrice = _livePrices[symbol];
                  final price = livePrice ?? (t['price'] as num).toDouble();
                  final change = (t['change_percent_24h'] as num).toDouble();
                  final isPositive = change >= 0;

                  return ListTile(
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => TradingScreen(symbol: symbol)),
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    leading: CircleAvatar(
                      backgroundColor: AppColors.card,
                      child: Text(
                        symbol.replaceAll('USDT', '').substring(0, 2),
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                      ),
                    ),
                    title: Text(
                      symbol.replaceAll('USDT', '/USDT'),
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    subtitle: Text(
                      'Vol: ${_formatVolume(t['volume_24h'])}',
                      style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
                    ),
                    trailing: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          '\$${_formatPrice(price)}',
                          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: (isPositive ? AppColors.green : AppColors.red).withOpacity(0.15),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            '${isPositive ? '+' : ''}${change.toStringAsFixed(2)}%',
                            style: TextStyle(
                              color: isPositive ? AppColors.green : AppColors.red,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
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

  String _formatPrice(double p) {
    if (p > 1000) return p.toStringAsFixed(2);
    if (p > 1) return p.toStringAsFixed(4);
    return p.toStringAsFixed(6);
  }

  String _formatVolume(dynamic v) {
    final vol = (v as num).toDouble();
    if (vol > 1e9) return '${(vol / 1e9).toStringAsFixed(1)}B';
    if (vol > 1e6) return '${(vol / 1e6).toStringAsFixed(1)}M';
    if (vol > 1e3) return '${(vol / 1e3).toStringAsFixed(1)}K';
    return vol.toStringAsFixed(0);
  }
}
