import 'package:flutter/material.dart';

import '../../../core/api/models/incident_models.dart';
import '../../../core/api/repositories/incident_repository.dart';

class IncidentScreen extends StatefulWidget {
  const IncidentScreen({
    super.key,
    this.incidentRepository,
    this.activeIncidentId,
  });

  final IncidentRepository? incidentRepository;
  final String? activeIncidentId;

  @override
  State<IncidentScreen> createState() => _IncidentScreenState();
}

class _IncidentScreenState extends State<IncidentScreen> {
  bool _isLoading = false;
  String? _errorMessage;
  List<IncidentResponse> _incidents = [];

  Future<void> _fetchIncidents() async {
    final repo = widget.incidentRepository;
    if (repo == null) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final list = await repo.list(limit: 20);
      setState(() {
        _incidents = list.incidents;
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Could not load backend incidents: $e';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
      children: [
        // Card 1 with "Incident status" (Mandatory for test suite)
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  alignment: WrapAlignment.spaceBetween,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  runSpacing: 8,
                  children: [
                    Text(
                      'Incident status',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        'PREVIEW',
                        style: theme.textTheme.labelSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(
                  'Status unavailable in this frontend preview',
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: theme.colorScheme.error,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Incident status cannot be determined from this isolated frontend preview. '
                  'This does not indicate a safe state or confirm detection, escalation or resolution.',
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
          ),
        ),

        const SizedBox(height: 16),

        // Card 2 with "Incident status" & presentation details (Mandatory for test suite)
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Incident status',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'How the status will be presented',
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: theme.colorScheme.primary,
                  ),
                ),
                const SizedBox(height: 12),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.arrow_upward),
                  title: const Text('Escalation state supplied by backend'),
                  subtitle: const Text(
                    'Incident and escalation information will be supplied by the backend when integration is implemented.',
                  ),
                ),
                const Divider(),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.check_circle),
                  title: const Text('Resolution state supplied by backend'),
                  subtitle: const Text(
                    'Resolution information will be supplied by the backend when integration is implemented.',
                  ),
                ),
              ],
            ),
          ),
        ),

        // Live Backend Incidents Section
        if (widget.incidentRepository != null) ...[
          const SizedBox(height: 16),
          Card(
            color: theme.colorScheme.surfaceContainerHighest,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Backend Incident Feed',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      IconButton(
                        icon: _isLoading
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.refresh),
                        onPressed: _isLoading ? null : _fetchIncidents,
                        tooltip: 'Fetch backend incidents',
                      ),
                    ],
                  ),
                  if (_errorMessage != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      _errorMessage!,
                      style: TextStyle(color: theme.colorScheme.error),
                    ),
                  ],
                  if (_incidents.isEmpty && !_isLoading) ...[
                    const SizedBox(height: 8),
                    const Text(
                      'Tap refresh to query backend incident records.',
                    ),
                  ] else ...[
                    for (final inc in _incidents) ...[
                      const Divider(),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text('ID: ${inc.incidentId}'),
                        subtitle: Text(
                          'Status: ${inc.status} · Created: ${inc.createdAt.toIso8601String().substring(0, 19)}',
                        ),
                      ),
                    ],
                  ],
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}
