/// LastMomentsBuffer — bounded in-memory recent-reading buffer.
///
/// Retains recent [HrSample] values for the Flutter Monitoring UI. This buffer
/// is distinct from the core detector's event-scoped evidence (which is
/// abnormal-only and event-scoped). It does not perform anomaly detection and
/// has no persistence layer, ORM model, or migration.
///
/// The buffer is bounded by sample count and retention window. Defaults are
/// 60 samples and a 30-second retention window, as proposed in the integration
/// contract.
library;

import 'dart:collection';
import 'dart:math' as math;

import '../../features/monitoring/domain/hr_sample.dart';

class LastMomentsBuffer {
  /// Maximum number of samples retained. Older samples are pruned when the
  /// limit is exceeded.
  final int maxSamples;

  /// Maximum retention window in milliseconds. Samples whose timestamp is
  /// older than [maxMs] milliseconds from the newest sample are rejected on
  /// [add].
  final int maxMs;

  /// Internal ordered queue of accepted samples, newest last.
  final ListQueue<HrSample> _samples;

  /// Count of rejected samples (duplicates and out-of-order timestamps).
  int _rejectionCount;

  /// Create a [LastMomentsBuffer].
  LastMomentsBuffer({this.maxSamples = 60, this.maxMs = 30000})
      : _samples = ListQueue<HrSample>(),
        _rejectionCount = 0;

  /// Add a recent [HrSample] to the buffer.
  ///
  /// Rules:
  ///   - Duplicate timestamps (same millisecond as the latest sample) are
  ///     rejected and increment [_rejectionCount].
  ///   - Out-of-order timestamps (not strictly newer than the latest accepted
  ///     sample) are rejected and increment [_rejectionCount].
  ///   - Accepted samples are normalized to UTC and appended chronologically.
  ///   - If adding a sample exceeds [maxSamples], the oldest sample is pruned.
  ///   - If a sample's timestamp is older than [maxMs] milliseconds from the
  ///     newest sample, it is rejected.
  void add(HrSample sample) {
    // Ensure UTC by converting if necessary.
    final ts = _normalizeToUtc(sample.ts);

    // If buffer is empty, accept unconditionally.
    if (_samples.isEmpty) {
      _samples.addLast(sample.copyWith(ts: ts));
      return;
    }

    // Get the latest sample's timestamp.
    final latestTs = _samples.last.ts;

    // Check for duplicate timestamp (same millisecond as latest).
    if (ts.millisecondsSinceEpoch == latestTs.millisecondsSinceEpoch) {
      _rejectionCount++;
      return;
    }

    // Check for out-of-order timestamp (not strictly newer than latest).
    if (ts.millisecondsSinceEpoch <= latestTs.millisecondsSinceEpoch) {
      _rejectionCount++;
      return;
    }

    // Check if the sample itself is already older than maxMs relative to latestTs (shouldn't happen since ts > latestTs).
    _samples.addLast(sample.copyWith(ts: ts));

    // Prune samples exceeding maxMs retention window relative to newest sample.
    while (_samples.length > 1 &&
        ts.difference(_samples.first.ts).inMilliseconds > maxMs) {
      _samples.removeFirst();
    }

    // Prune samples exceeding maxSamples.
    while (_samples.length > maxSamples) {
      _samples.removeFirst();
    }
  }

  /// Return the [limit] most recent samples in chronological order (oldest first).
  /// Defaults to [maxSamples].
  List<HrSample> recent({int? limit}) {
    final effectiveLimit = (limit ?? maxSamples).clamp(1, maxSamples);
    final list = _samples.toList();
    if (list.length <= effectiveLimit) {
      return List.unmodifiable(list);
    }
    return List.unmodifiable(list.sublist(list.length - effectiveLimit));
  }

  /// Return a snapshot of samples whose timestamps fall within [start, end], inclusive.
  HrBufferSnapshot window(DateTime start, DateTime end) {
    final startUtc = _normalizeToUtc(start);
    final endUtc = _normalizeToUtc(end);

    final windowSamples = <HrSample>[];
    for (final sample in _samples) {
      final ts = _normalizeToUtc(sample.ts);
      if ((ts.isAfter(startUtc) || ts.isAtSameMomentAs(startUtc)) &&
          (ts.isBefore(endUtc) || ts.isAtSameMomentAs(endUtc))) {
        windowSamples.add(sample);
      }
    }

    int? minHr;
    int? maxHr;
    DateTime? firstTs;
    DateTime? lastTs;

    if (windowSamples.isNotEmpty) {
      firstTs = windowSamples.first.ts;
      lastTs = windowSamples.last.ts;
      minHr = windowSamples.map((s) => s.hr).reduce(math.min);
      maxHr = windowSamples.map((s) => s.hr).reduce(math.max);
    }

    return HrBufferSnapshot(
      samples: List.unmodifiable(windowSamples),
      firstHr: minHr,
      lastHr: maxHr,
      firstTs: firstTs,
      lastTs: lastTs,
      rejectionCount: _rejectionCount,
    );
  }

  /// Clear all samples and reset the rejection count.
  void reset() {
    _samples.clear();
    _rejectionCount = 0;
  }

  /// Normalize a [DateTime] to UTC.
  DateTime _normalizeToUtc(DateTime ts) {
    return ts.isUtc ? ts : ts.toUtc();
  }

  /// Number of samples currently buffered.
  int get sampleCount => _samples.length;

  /// Number of rejected samples (cumulative since last reset).
  int get rejectionCount => _rejectionCount;

  @override
  String toString() =>
      'LastMomentsBuffer(sampleCount: $sampleCount, rejectionCount: $_rejectionCount)';
}

/// HrBufferSnapshot — snapshot of buffer state within a time window.
///
/// Returned by [LastMomentsBuffer.window].
class HrBufferSnapshot {
  /// The retained samples whose timestamps fall within the requested window.
  final List<HrSample> samples;

  /// The minimum heart rate among the sampled values in the window.
  final int? firstHr;

  /// The maximum heart rate among the sampled values in the window.
  final int? lastHr;

  /// The earliest timestamp among the sampled values in the window.
  final DateTime? firstTs;

  /// The latest timestamp among the sampled values in the window.
  final DateTime? lastTs;

  /// The cumulative count of rejected samples since the buffer was last reset.
  final int rejectionCount;

  /// Create a [HrBufferSnapshot].
  HrBufferSnapshot({
    required this.samples,
    required this.firstHr,
    required this.lastHr,
    required this.firstTs,
    required this.lastTs,
    required this.rejectionCount,
  });

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is HrBufferSnapshot &&
        other.samples == samples &&
        other.firstHr == firstHr &&
        other.lastHr == lastHr &&
        other.firstTs == firstTs &&
        other.lastTs == lastTs &&
        other.rejectionCount == rejectionCount;
  }

  @override
  int get hashCode => Object.hash(
        samples,
        firstHr,
        lastHr,
        firstTs,
        lastTs,
        rejectionCount,
      );

  @override
  String toString() =>
      'HrBufferSnapshot(samples: ${samples.length}, firstHr: $firstHr, lastHr: $lastHr)';
}
