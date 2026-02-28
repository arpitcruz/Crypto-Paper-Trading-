import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _baseUrl = String.fromEnvironment('API_URL', defaultValue: 'http://10.0.2.2:8000/api/v1');

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;

  late final Dio _dio;
  final _storage = const FlutterSecureStorage();

  ApiService._internal() {
    _dio = Dio(BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      headers: {'Content-Type': 'application/json'},
    ));

    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: 'access_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (err, handler) async {
        if (err.response?.statusCode == 401) {
          // Try to refresh token
          final refreshed = await _refreshToken();
          if (refreshed) {
            // Retry original request
            final token = await _storage.read(key: 'access_token');
            err.requestOptions.headers['Authorization'] = 'Bearer $token';
            final response = await _dio.fetch(err.requestOptions);
            return handler.resolve(response);
          }
        }
        return handler.next(err);
      },
    ));
  }

  Future<bool> _refreshToken() async {
    try {
      final refreshToken = await _storage.read(key: 'refresh_token');
      if (refreshToken == null) return false;
      final res = await _dio.post('/auth/refresh', data: {'refresh_token': refreshToken});
      await _storage.write(key: 'access_token', value: res.data['access_token']);
      await _storage.write(key: 'refresh_token', value: res.data['refresh_token']);
      return true;
    } catch (_) {
      return false;
    }
  }

  // Auth
  Future<Map<String, dynamic>> login(String email, String password) async {
    final res = await _dio.post('/auth/login', data: {'email': email, 'password': password});
    await _storage.write(key: 'access_token', value: res.data['access_token']);
    await _storage.write(key: 'refresh_token', value: res.data['refresh_token']);
    return res.data;
  }

  Future<Map<String, dynamic>> register(String email, String username, String password) async {
    final res = await _dio.post('/auth/register', data: {
      'email': email, 'username': username, 'password': password,
    });
    return res.data;
  }

  Future<void> logout(String refreshToken) async {
    await _dio.post('/auth/logout', data: {'refresh_token': refreshToken});
    await _storage.deleteAll();
  }

  // User
  Future<Map<String, dynamic>> getProfile() async {
    final res = await _dio.get('/users/me');
    return res.data;
  }

  // Wallet
  Future<List<dynamic>> getWallets() async {
    final res = await _dio.get('/trading/wallet');
    return res.data;
  }

  Future<void> transferFunds(double amount, String from, String to) async {
    await _dio.post('/trading/wallet/transfer', data: {
      'amount': amount, 'from_wallet': from, 'to_wallet': to,
    });
  }

  Future<void> resetWallet() async {
    await _dio.post('/trading/wallet/reset');
  }

  // Market
  Future<List<dynamic>> getTickers() async {
    final res = await _dio.get('/market/tickers');
    return res.data['tickers'];
  }

  Future<Map<String, dynamic>> getTicker(String symbol) async {
    final res = await _dio.get('/market/ticker/$symbol');
    return res.data;
  }

  Future<List<dynamic>> getKlines(String symbol, String interval) async {
    final res = await _dio.get('/market/klines/$symbol', queryParameters: {'interval': interval});
    return res.data['data'];
  }

  Future<Map<String, dynamic>> getOrderbook(String symbol) async {
    final res = await _dio.get('/market/orderbook/$symbol');
    return res.data;
  }

  // Orders
  Future<Map<String, dynamic>> placeOrder(Map<String, dynamic> orderData) async {
    final res = await _dio.post('/trading/orders', data: orderData);
    return res.data;
  }

  Future<List<dynamic>> getOrders({String? status, String? symbol}) async {
    final res = await _dio.get('/trading/orders', queryParameters: {
      if (status != null) 'status': status,
      if (symbol != null) 'symbol': symbol,
    });
    return res.data;
  }

  Future<void> cancelOrder(String orderId) async {
    await _dio.delete('/trading/orders/$orderId');
  }

  // Positions
  Future<List<dynamic>> getPositions() async {
    final res = await _dio.get('/trading/positions');
    return res.data;
  }

  Future<void> closePosition(String positionId, {double? quantity}) async {
    await _dio.post('/trading/positions/close', data: {
      'position_id': positionId,
      if (quantity != null) 'quantity': quantity,
    });
  }

  // Trades
  Future<List<dynamic>> getTrades() async {
    final res = await _dio.get('/trading/trades');
    return res.data;
  }

  // Stats
  Future<Map<String, dynamic>> getStats() async {
    final res = await _dio.get('/trading/stats');
    return res.data;
  }

  // Alerts
  Future<List<dynamic>> getAlerts() async {
    final res = await _dio.get('/users/me/alerts');
    return res.data;
  }

  Future<void> createAlert(String symbol, double price, String condition) async {
    await _dio.post('/users/me/alerts', data: {
      'symbol': symbol, 'target_price': price, 'condition': condition,
    });
  }
}
