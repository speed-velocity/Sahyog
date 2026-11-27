import 'package:flutter/material.dart';

import '../../../core/api/api_exception.dart';
import '../../../core/api/api_session.dart';
import '../../../core/api/models/auth_models.dart';
import '../../../core/api/repositories/authentication_repository.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({
    super.key,
    required this.authRepository,
    required this.session,
    this.onAuthenticated,
  });

  final AuthenticationRepository authRepository;
  final ApiSession session;
  final VoidCallback? onAuthenticated;

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  bool _isRegistering = false;
  bool _isLoading = false;
  bool _obscurePassword = true;
  String? _errorMessage;
  String? _successMessage;

  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  String _selectedRole = 'SUBJECT';

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
    });

    final username = _usernameController.text.trim();
    final password = _passwordController.text;

    try {
      if (_isRegistering) {
        final response = await widget.authRepository.register(
          RegistrationRequest(
            loginIdentifier: username,
            password: password,
            role: _selectedRole,
          ),
        );
        setState(() {
          _successMessage = 'Registered as ${response.role}! Signing in...';
        });
        // Auto sign-in after registration
        await widget.authRepository.login(
          username: username,
          password: password,
        );
      } else {
        await widget.authRepository.login(
          username: username,
          password: password,
        );
      }

      if (mounted) {
        widget.onAuthenticated?.call();
        Navigator.of(context).maybePop();
      }
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          _errorMessage = error.message;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'An unexpected error occurred: $e';
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _logout() {
    widget.authRepository.logout();
    setState(() {
      _successMessage = 'Signed out successfully.';
    });
    widget.onAuthenticated?.call();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isAuthenticated = widget.session.isAuthenticated;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          isAuthenticated
              ? 'Account Session'
              : (_isRegistering ? 'Register' : 'Sign In'),
        ),
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Card(
              elevation: 2,
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: isAuthenticated
                    ? _buildAuthenticatedView(theme)
                    : _buildAuthForm(theme),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildAuthenticatedView(ThemeData theme) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Icon(Icons.check_circle_outline, color: Colors.green, size: 64),
        const SizedBox(height: 16),
        Text(
          'Active Session Authenticated',
          style: theme.textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 8),
        Text(
          'Access token is held securely in-memory for this runtime only. It will be cleared when the app closes or when you sign out.',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.outline,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 24),
        FilledButton.tonalIcon(
          onPressed: _logout,
          icon: const Icon(Icons.logout),
          label: const Text('Sign Out'),
        ),
      ],
    );
  }

  Widget _buildAuthForm(ThemeData theme) {
    return Form(
      key: _formKey,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            _isRegistering ? 'Create Sahyog Account' : 'Sign In to Sahyog',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            _isRegistering
                ? 'Register as a monitored subject or caregiver.'
                : 'Enter your credentials to access live backend monitoring.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.outline,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),

          if (_errorMessage != null) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.errorContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                _errorMessage!,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onErrorContainer,
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],

          if (_successMessage != null) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                _successMessage!,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onPrimaryContainer,
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],

          TextFormField(
            controller: _usernameController,
            decoration: const InputDecoration(
              labelText: 'Username / Identifier',
              prefixIcon: Icon(Icons.person_outline),
              border: OutlineInputBorder(),
            ),
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return 'Please enter your username';
              }
              if (_isRegistering && value.trim().length < 3) {
                return 'Username must be at least 3 characters';
              }
              return null;
            },
          ),
          const SizedBox(height: 16),

          TextFormField(
            controller: _passwordController,
            obscureText: _obscurePassword,
            decoration: InputDecoration(
              labelText: 'Password',
              prefixIcon: const Icon(Icons.lock_outline),
              border: const OutlineInputBorder(),
              suffixIcon: IconButton(
                icon: Icon(
                  _obscurePassword
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                ),
                onPressed: () =>
                    setState(() => _obscurePassword = !_obscurePassword),
              ),
            ),
            validator: (value) {
              if (value == null || value.isEmpty) {
                return 'Please enter your password';
              }
              if (_isRegistering && value.length < 6) {
                return 'Password must be at least 6 characters';
              }
              return null;
            },
          ),
          const SizedBox(height: 16),

          if (_isRegistering) ...[
            DropdownButtonFormField<String>(
              initialValue: _selectedRole,
              decoration: const InputDecoration(
                labelText: 'Account Role',
                prefixIcon: Icon(Icons.badge_outlined),
                border: OutlineInputBorder(),
              ),
              items: const [
                DropdownMenuItem(
                  value: 'SUBJECT',
                  child: Text('Subject (Monitored Person)'),
                ),
                DropdownMenuItem(
                  value: 'CAREGIVER',
                  child: Text('Caregiver (Dashboard Access)'),
                ),
              ],
              onChanged: (val) {
                if (val != null) setState(() => _selectedRole = val);
              },
            ),
            const SizedBox(height: 20),
          ],

          FilledButton(
            onPressed: _isLoading ? null : _submit,
            child: _isLoading
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(_isRegistering ? 'Register' : 'Sign In'),
          ),
          const SizedBox(height: 12),

          TextButton(
            onPressed: _isLoading
                ? null
                : () {
                    setState(() {
                      _isRegistering = !_isRegistering;
                      _errorMessage = null;
                      _successMessage = null;
                    });
                  },
            child: Text(
              _isRegistering
                  ? 'Already have an account? Sign In'
                  : "Don't have an account? Register",
            ),
          ),
        ],
      ),
    );
  }
}
