import 'package:flutter/material.dart';

enum AsyncPanelState {
  loading,
  error,
}

class AsyncStatePanel extends StatelessWidget {
  const AsyncStatePanel({
    super.key,
    required this.state,
    required this.title,
    required this.message,
    this.onRetry,
  });

  final AsyncPanelState state;
  final String title;
  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              message,
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            if (state == AsyncPanelState.loading)
              const LinearProgressIndicator()
            else if (state == AsyncPanelState.error && onRetry != null)
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.tonal(
                  onPressed: onRetry,
                  child: const Text('Try again'),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
