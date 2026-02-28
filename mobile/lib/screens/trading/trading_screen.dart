import 'package:flutter/material.dart';
import '../../services/api_service.dart';
import '../../services/websocket_service.dart';
import '../../utils/app_theme.dart';

class TradingScreen extends StatefulWidget {
  final String symbol;
  const TradingScreen({super.key, this.symbol = 'BTCUSDT'});

  @override
  State<TradingScreen> createState() => _TradingScreenState();
}

class _TradingScreenState extends State<TradingScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  String _orderType = 'market'; // market | limit
  String _side = 'buy'; // buy | sell
  String _marketType = 'spot'; // spot | futures
  int _leverage = 10;
  double? _currentPrice;
  final _quantityCtrl = TextEditingController();
  final _priceCtrl = TextEditingController();
  final _tpCtrl = TextEditingController();
  final _slCtrl = TextEditingController();
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadPrice();
    WebSocketService().priceStream.listen((msg) {
      if (msg['type'] == 'ticker' && msg['symbol'] == widget.symbol && mounted) {
        setState(() => _currentPrice = (msg['price'] as num).toDouble());
      }
    });
    WebSocketService().subscribeTo(widget.symbol);
  }

  Future<void> _loadPrice() async {
    try {
      final ticker = await ApiService().getTicker(widget.symbol);
      setState(() => _currentPrice = (ticker['price'] as num).toDouble());
    } catch (_) {}
  }

  Future<void> _placeOrder() async {
    if (_quantityCtrl.text.isEmpty) return;
    setState(() => _loading = true);
    try {
      await ApiService().placeOrder({
        'symbol': widget.symbol,
        'market_type': _marketType,
        'order_type': _orderType,
        'side': _side,
        'quantity': double.parse(_quantityCtrl.text),
        if (_orderType == 'limit') 'price': double.parse(_priceCtrl.text),
        if (_marketType == 'futures') 'leverage': _leverage,
        if (_tpCtrl.text.isNotEmpty) 'take_profit': double.parse(_tpCtrl.text),
        if (_slCtrl.text.isNotEmpty) 'stop_loss': double.parse(_slCtrl.text),
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Order placed: ${_side.toUpperCase()} ${_quantityCtrl.text} ${widget.symbol}'),
          backgroundColor: _side == 'buy' ? AppColors.green : AppColors.red,
        ),
      );
      _quantityCtrl.clear();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e'), backgroundColor: AppColors.red),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.symbol.replaceAll('USDT', '/USDT')),
            if (_currentPrice != null)
              Text(
                '\$${_currentPrice!.toStringAsFixed(2)}',
                style: const TextStyle(fontSize: 13, color: AppColors.green),
              ),
          ],
        ),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [Tab(text: 'Spot'), Tab(text: 'Futures')],
          onTap: (i) => setState(() => _marketType = i == 0 ? 'spot' : 'futures'),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            // Buy/Sell toggle
            Row(
              children: [
                Expanded(
                  child: GestureDetector(
                    onTap: () => setState(() => _side = 'buy'),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      decoration: BoxDecoration(
                        color: _side == 'buy' ? AppColors.green : AppColors.surface,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        'Buy / Long',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: _side == 'buy' ? Colors.white : AppColors.textSecondary,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: GestureDetector(
                    onTap: () => setState(() => _side = 'sell'),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      decoration: BoxDecoration(
                        color: _side == 'sell' ? AppColors.red : AppColors.surface,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        'Sell / Short',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: _side == 'sell' ? Colors.white : AppColors.textSecondary,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Order type
            Row(
              children: ['market', 'limit'].map((type) {
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: GestureDetector(
                    onTap: () => setState(() => _orderType = type),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(
                        color: _orderType == type ? AppColors.primary.withOpacity(0.2) : Colors.transparent,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                          color: _orderType == type ? AppColors.primary : AppColors.border,
                        ),
                      ),
                      child: Text(
                        type[0].toUpperCase() + type.substring(1),
                        style: TextStyle(
                          color: _orderType == type ? AppColors.primary : AppColors.textSecondary,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 16),

            // Leverage (futures only)
            if (_marketType == 'futures') ...[
              Row(
                children: [
                  const Text('Leverage:', style: TextStyle(color: AppColors.textSecondary)),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Slider(
                      value: _leverage.toDouble(),
                      min: 1, max: 100, divisions: 99,
                      label: '${_leverage}x',
                      activeColor: AppColors.primary,
                      onChanged: (v) => setState(() => _leverage = v.round()),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.yellow.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      '${_leverage}x',
                      style: const TextStyle(color: AppColors.yellow, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
            ],

            // Quantity
            TextField(
              controller: _quantityCtrl,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                labelText: 'Quantity',
                suffixText: 'Units',
              ),
            ),
            const SizedBox(height: 12),

            // Price (limit only)
            if (_orderType == 'limit') ...[
              TextField(
                controller: _priceCtrl,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Limit Price', suffixText: 'USDT'),
              ),
              const SizedBox(height: 12),
            ],

            // TP/SL
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _tpCtrl,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Take Profit', suffixText: '✓'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: _slCtrl,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Stop Loss', suffixText: '✗'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // Place order button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _loading ? null : _placeOrder,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _side == 'buy' ? AppColors.green : AppColors.red,
                ),
                child: _loading
                    ? const SizedBox(
                        width: 20, height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : Text(
                        '${_side == 'buy' ? 'Buy' : 'Sell'} ${widget.symbol.replaceAll('USDT', '')}',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
