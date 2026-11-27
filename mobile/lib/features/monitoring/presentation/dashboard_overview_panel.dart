import 'package:flutter/material.dart';

import '../../../core/api/models/dashboard_models.dart';
import '../../../shared/widgets/async_state_panel.dart';
import 'dashboard_overview_controller.dart';

class DashboardOverviewPanel extends StatelessWidget {
  const DashboardOverviewPanel({super.key, required this.controller});

  final DashboardOverviewController controller;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: controller,
      builder: (context, _) {
        return switch (controller.state) {
          DashboardOverviewState.unauthenticated => const _MessageCard(
            title: 'Sign-in required',
            message: 'Authenticate to load dashboard data. No protected API request was sent.',
          ),
          DashboardOverviewState.loading => const AsyncStatePanel(
            state: AsyncPanelState.loading,
            title: 'Backend dashboard',
            message: 'Loading the latest dashboard response…',
          ),
          DashboardOverviewState.error => AsyncStatePanel(
            state: AsyncPanelState.error,
            title: 'Dashboard unavailable',
            message:
                controller.errorMessage ??
                'Dashboard data could not be loaded.',
            onRetry: controller.load,
          ),
          DashboardOverviewState.ready => _DashboardDataCard(
            overview: controller.overview!,
          ),
        };
      },
    );
  }
}

class _DashboardDataCard extends StatelessWidget {
  const _DashboardDataCard({required this.overview});

  final DashboardOverviewResponse overview;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Backend dashboard response',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            _Field(label: 'Subject ID', value: overview.subjectUserId),
            _Field(
              label: 'Monitoring status',
              value: overview.monitoringStatus,
            ),
            _Field(
              label: 'Latest reading',
              value: _readingValue(overview.latestReading),
            ),
            if (overview.latestReading != null) ...[
              _Field(
                label: 'Reading source',
                value: overview.latestReading!.sourceKind,
              ),
              _Field(
                label: 'Reading observed at',
                value: overview.latestReading!.observedAt.toIso8601String(),
              ),
            ],
            _Field(
              label: 'Active incident',
              value: overview.activeIncident ?? 'None reported by backend',
            ),
            _Field(
              label: 'Incident status',
              value: overview.incidentStatus ?? 'Unavailable',
            ),
            _Field(
              label: 'Latest update',
              value:
                  overview.latestUpdateAt?.toIso8601String() ?? 'Unavailable',
            ),
          ],
        ),
      ),
    );
  }

  String _readingValue(LatestReadingSummary? reading) {
    if (reading == null) return 'Unavailable';
    return '${reading.heartRateBpm} bpm';
  }
}

class _Field extends StatelessWidget {
  const _Field({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: SelectableText('$label: $value'),
    );
  }
}

class _MessageCard extends StatelessWidget {
  const _MessageCard({required this.title, required this.message});

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(message),
          ],
        ),
      ),
    );
  }
}
