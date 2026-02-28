import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _wsBase = String.fromEnvironment('WS_URL', defaultValue: 'ws://10.0.2.2:8000');

class WebSocketService {
  static final WebSocketService _instance = WebSocketService._internal();
  factory WebSocketService() => _instance;
  WebSocketService._internal();

  WebSocketChannel? _marketChannel;
  WebSocketChannel? _userChannel;
  final _storage = const FlutterSecureStorage();

  final _priceController = StreamController<Map<String, dynamic>>.broadcast();
  final _userController = StreamController<Map<String, dynamic>>.broadcast();

  Stream<Map<String, dynamic>> get priceStream => _priceController.stream;
  Stream<Map<String, dynamic>> get userStream => _userController.stream;

  void connectMarket() {
    _marketChannel?.sink.close();
    _marketChannel = WebSocketChannel.connect(Uri.parse('$_wsBase/ws/market'));
    _marketChannel!.stream.listen(
      (data) {
        final decoded = jsonDecode(data as String);
        _priceController.add(decoded);
      },
      onError: (_) => Future.delayed(const Duration(seconds: 3), connectMarket),
      onDone: () => Future.delayed(const Duration(seconds: 3), connectMarket),
    );
  }

  Future<void> connectUser() async {
    final token = await _storage.read(key: 'access_token');
    if (token == null) return;

    _userChannel?.sink.close();
    _userChannel = WebSocketChannel.connect(
      Uri.parse('$_wsBase/ws/user?token=$token'),
    );
    _userChannel!.stream.listen(
      (data) {
        final decoded = jsonDecode(data as String);
        _userController.add(decoded);
      },
      onError: (_) => Future.delayed(const Duration(seconds: 5), connectUser),
      onDone: () => Future.delayed(const Duration(seconds: 5), connectUser),
    );
  }

  void subscribeTo(String symbol) {
    _marketChannel?.sink.add(jsonEncode({'action': 'subscribe', 'symbol': symbol}));
  }

  void ping() {
    _marketChannel?.sink.add(jsonEncode({'action': 'ping'}));
  }

  void dispose() {
    _marketChannel?.sink.close();
    _userChannel?.sink.close();
    _priceController.close();
    _userController.close();
  }
}
