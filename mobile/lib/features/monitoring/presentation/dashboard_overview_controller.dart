import 'package:flutter/foundation.dart';

import '../../../core/api/api_exception.dart';
import '../../../core/api/api_session.dart';
import '../../../core/api/models/dashboard_models.dart';
import '../../../core/api/repositories/dashboard_repository.dart';

enum DashboardOverviewState { unauthenticated, loading, error, ready }

class DashboardOverviewController extends ChangeNotifier {
  DashboardOverviewController({
    required this.session,
    required this.repository,
    this.configurationError,
  }) : _state = session.isAuthenticated
           ? DashboardOverviewState.loading
           : DashboardOverviewState.unauthenticated;

  final ApiSession session;
  final DashboardRepository? repository;
  final String? configurationError;

  DashboardOverviewState _state;
  DashboardOverviewResponse? _overview;
  String? _errorMessage;
  int _requestGeneration = 0;
  bool _disposed = false;

  DashboardOverviewState get state => _state;
  DashboardOverviewResponse? get overview => _overview;
  String? get errorMessage => _errorMessage;

  Future<void> load() async {
    final generation = ++_requestGeneration;
    if (!session.isAuthenticated) {
      _overview = null;
      _errorMessage = null;
      _state = DashboardOverviewState.unauthenticated;
      _notifyIfActive();
      return;
    }

    final api = repository;
    if (api == null || configurationError != null) {
      _overview = null;
      _errorMessage =
          configurationError ??
          'The dashboard API is not configured. Set SAHYOG_API_BASE_URL.';
      _state = DashboardOverviewState.error;
      _notifyIfActive();
      return;
    }

    _state = DashboardOverviewState.loading;
    _errorMessage = null;
    _notifyIfActive();
    try {
      final result = await api.getOverview();
      if (_disposed || generation != _requestGeneration) return;
      _overview = result;
      _state = DashboardOverviewState.ready;
    } on ApiException catch (error) {
      if (_disposed || generation != _requestGeneration) return;
      _overview = null;
      _errorMessage = error.message;
      _state = DashboardOverviewState.error;
    } catch (_) {
      if (_disposed || generation != _requestGeneration) return;
      _overview = null;
      _errorMessage = 'Dashboard data could not be loaded. Please try again.';
      _state = DashboardOverviewState.error;
    }
    _notifyIfActive();
  }

  void _notifyIfActive() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _requestGeneration++;
    super.dispose();
  }
}
