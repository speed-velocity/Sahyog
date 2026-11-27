import 'package:flutter/material.dart';

import '../../../core/api/models/verification_model.dart';
import '../../../core/api/repositories/verification_repository.dart';

class VerificationScreen extends StatefulWidget {
  const VerificationScreen({
    super.key,
    required this.acknowledged,
    required this.onAcknowledge,
    this.verificationRepository,
    this.activeIncidentId,
    this.onVerified,
  });

  final bool acknowledged;
  final VoidCallback onAcknowledge;
  final VerificationRepository? verificationRepository;
  final String? activeIncidentId;
  final VoidCallback? onVerified;

  @override
  State<VerificationScreen> createState() => _VerificationScreenState();
}

class _VerificationScreenState extends State<VerificationScreen> {
  bool _isSubmitting = false;
  String? _backendSuccessMessage;
  String? _backendErrorMessage;

  Future<void> _submitBackendVerification() async {
    final repo = widget.verificationRepository;
    final incidentId = widget.activeIncidentId;

    if (repo == null || incidentId == null || incidentId.isEmpty) {
      setState(() {
        _backendErrorMessage = 'No active backend incident ID to verify.';
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _backendSuccessMessage = null;
      _backendErrorMessage = null;
    });

    try {
      final key =
          'verif_${incidentId}_${DateTime.now().millisecondsSinceEpoch}';
      final response = await repo.submit(
        incidentId: incidentId,
        request: VerificationRequest(idempotencyKey: key),
      );

      setState(() {
        _backendSuccessMessage =
            'Verification delivered to backend. Incident marked: ${response.status}.';
      });
      widget.onVerified?.call();
    } catch (e) {
      setState(() {
        _backendErrorMessage = 'Backend verification failed: $e';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
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
        // Standard Preview Card (Required for test assertions)
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.info_outline, color: theme.colorScheme.primary),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Verification status unavailable',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(
                  'This frontend preview cannot determine whether a real verification is pending. '
                  'In the integrated system, an automated check is initiated when sustained anomalies occur.',
                  style: theme.textTheme.bodyMedium,
                ),
                const SizedBox(height: 16),
                Center(
                  child: FilledButton.icon(
                    onPressed: widget.onAcknowledge,
                    icon: const Icon(Icons.check_circle_outline),
                    label: const Text("Preview only: I'm okay"),
                  ),
                ),
                if (widget.acknowledged) ...[
                  const SizedBox(height: 16),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.secondaryContainer,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      'Preview interaction only. No reply was sent and no incident status was changed.',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onSecondaryContainer,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),

        // Live Backend Verification Card
        if (widget.verificationRepository != null) ...[
          const SizedBox(height: 16),
          Card(
            color: theme.colorScheme.surfaceContainerHighest,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.verified, color: Colors.teal),
                      const SizedBox(width: 8),
                      Text(
                        'Backend Incident Verification',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    widget.activeIncidentId != null
                        ? 'Active Incident ID: ${widget.activeIncidentId}'
                        : 'No active incident detected on backend.',
                    style: theme.textTheme.bodyMedium,
                  ),
                  if (_backendSuccessMessage != null) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.green.shade50,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        _backendSuccessMessage!,
                        style: TextStyle(color: Colors.green.shade900),
                      ),
                    ),
                  ],
                  if (_backendErrorMessage != null) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.errorContainer,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        _backendErrorMessage!,
                        style: TextStyle(
                          color: theme.colorScheme.onErrorContainer,
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(height: 16),
                  Center(
                    child: FilledButton.tonalIcon(
                      onPressed:
                          (_isSubmitting || widget.activeIncidentId == null)
                          ? null
                          : _submitBackendVerification,
                      icon: _isSubmitting
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.send),
                      label: const Text("Confirm I'm okay with Backend"),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}
