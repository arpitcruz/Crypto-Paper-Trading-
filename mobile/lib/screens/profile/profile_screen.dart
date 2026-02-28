import 'package:flutter/material.dart';
import '../../services/api_service.dart';
import '../../services/websocket_service.dart';
import '../../utils/app_theme.dart';
import '../auth/login_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  Map<String, dynamic>? _profile;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      final profile = await ApiService().getProfile();
      setState(() => _profile = profile);
    } catch (_) {}
  }

  Future<void> _logout() async {
    WebSocketService().dispose();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (_) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = _profile;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Profile')),
      body: p == null
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Avatar
                Center(
                  child: Column(
                    children: [
                      CircleAvatar(
                        radius: 40,
                        backgroundColor: AppColors.primary,
                        child: Text(
                          (p['username'] as String)[0].toUpperCase(),
                          style: const TextStyle(fontSize: 32, color: Colors.white, fontWeight: FontWeight.bold),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        p['username'] as String,
                        style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                      ),
                      Text(
                        p['email'] as String,
                        style: const TextStyle(color: AppColors.textSecondary),
                      ),
                      if (p['role'] == 'admin') ...[
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppColors.yellow.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: const Text('Admin', style: TextStyle(color: AppColors.yellow)),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 32),

                // Info cards
                Card(
                  child: Column(
                    children: [
                      _buildTile('Full Name', p['full_name'] ?? 'Not set'),
                      const Divider(color: AppColors.border, height: 1),
                      _buildTile('Member Since', _formatDate(p['created_at'] as String)),
                      const Divider(color: AppColors.border, height: 1),
                      _buildTile('Auth Provider', p['auth_provider'] as String),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // Logout
                ElevatedButton(
                  onPressed: _logout,
                  style: ElevatedButton.styleFrom(backgroundColor: AppColors.red),
                  child: const Text('Sign Out'),
                ),
              ],
            ),
    );
  }

  Widget _buildTile(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppColors.textSecondary)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }

  String _formatDate(String date) {
    final d = DateTime.parse(date);
    return '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  }
}
