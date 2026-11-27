import 'package:flutter/material.dart';

enum ConnectionDisplayState {
  connecting,
  connected,
  disconnected,
}

enum ReadingDisplayState {
  noReadings,
  available,
  unavailableOrInvalid,
}

class MonitoringReadingPanel extends StatelessWidget {
  const MonitoringReadingPanel({
    super.key,
    required this.connectionState,
    required this.readingState,
    this.latestBpm,
    this.timestampLabel,
  });

  final ConnectionDisplayState connectionState;
  final ReadingDisplayState readingState;
  final int? latestBpm;
  final String? timestampLabel;

  String get _connectionLabel => switch (connectionState) {
        ConnectionDisplayState.connecting => 'Connecting',
        ConnectionDisplayState.connected => 'Connected',
        ConnectionDisplayState.disconnected => 'Disconnected',
      };

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isInvalid = readingState == ReadingDisplayState.unavailableOrInvalid ||
        (readingState == ReadingDisplayState.available && latestBpm == null);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
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
                  _connectionLabel,
                  style: theme.textTheme.titleMedium,
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    _connectionLabel.toUpperCase(),
                    style: theme.textTheme.labelSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (readingState == ReadingDisplayState.noReadings) ...[
              Text(
                'No readings available',
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: 4),
              Text(
                'No reading timestamp available',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.outline,
                ),
              ),
            ] else if (readingState == ReadingDisplayState.available &&
                latestBpm != null) ...[
              Text(
                '$latestBpm',
                style: theme.textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Latest reading timestamp',
                style: theme.textTheme.labelMedium?.copyWith(
                  color: theme.colorScheme.outline,
                ),
              ),
              if (timestampLabel != null)
                Text(
                  timestampLabel!,
                  style: theme.textTheme.bodySmall,
                ),
            ] else if (isInvalid) ...[
              Text(
                'Reading unavailable or invalid',
                style: theme.textTheme.bodyLarge?.copyWith(
                  color: theme.colorScheme.error,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              if (readingState == ReadingDisplayState.available &&
                  latestBpm == null)
                Text(
                  'The latest reading is missing its BPM value.',
                  style: theme.textTheme.bodyMedium,
                )
              else
                Text(
                  timestampLabel ?? 'Timestamp unavailable',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.outline,
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}
