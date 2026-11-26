/// LastMomentsBuffer — bounded in-memory recent-reading buffer.

/// Retains recent [HrSample] values for the Flutter Monitoring UI. This buffer
/// is distinct from the core detector's event-scoped evidence (which is
/// abnormal-only and event-scoped). It does not perform anomaly detection and
/// has no persistence layer, ORM model, or migration.

/// The buffer is bounded by sample count and retention window. Defaults are
/// 60 samples and a 30-second retention window, as proposed in the integration
/// contract.

import 'dart:collection';

import '../domain/hr_sample.dart';

class LastMomentsBuffer {
  /// Maximum number of samples retained. Older samples are pruned when the
  /// limit is exceeded.
  final int maxSamples;

  /// Maximum retention window in milliseconds. Samples whose timestamp is
  /// older than [maxMs] milliseconds from the newest sample are rejected on
  /// [add].
  final int maxMs;

  /// Internal ordered deque of accepted samples, newest last.
  final Deque<HrSample> _samples;

  /// Count of rejected samples (duplicates and out-of-order timestamps).
  int _rejectionCount;

  /// Create a [LastMomentsBuffer].
  LastMomentsBuffer({int maxSamples = 60, int maxMs = 30000})
      : maxSamples = maxSamples,
        maxMs = maxMs,
        _samples = Deque<HrSample>(),
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

    // Check for duplicate timestamp (same second/millisecond as latest).
    if (ts.millisecondsSinceEpoch == latestTs.millisecondsSinceEpoch) {
      _rejectionCount++;
      return;
    }

    // Check for out-of-order timestamp (not strictly newer than latest).
    if (ts.millisecondsSinceEpoch <= latestTs.millisecondsSinceEpoch) {
      _rejectionCount++;
      return;
    }

    // Check retention window: sample must be within maxMs of the newest sample.
    final ageMs = latestTs.difference(ts).inMilliseconds;
    if (ageMs > maxMs) {
      // Sample is too old relative to the newest; reject it.
      // But we still keep the existing samples; just don't add this one.
      _rejectionCount++;
      return;
    }

    // Add the sample.
    _samples.addLast(sample.copyWith(ts: ts));

    // Prune oldest samples if exceeding maxSamples.
    while (_samples.length > maxSamples) {
      _samples.removeFirst();
    }
  }

  /// Return the [limit] most recent samples in chronological order (oldest
  /// first). Defaults to [maxSamples].
  ///
  /// The returned list is a snapshot; modifications to the returned list do
  /// not affect the buffer.
  List<HrSample> recent([int limit]) {
    limit ??= maxSamples;
    limit = limit.clamp(1, maxSamples);

    // Return in chronological order (oldest first).
    final result = <HrSample>[];
    final startIdx = _samples.length - limit;
    for (int i = max(startIdx, 0); i < _samples.length; i++) {
      result.add(_samples[i]);
    }
    return result;
  }

  /// Return a snapshot of samples whose timestamps fall within [start, end],
  /// inclusive.
  ///
  /// The returned [HrBufferSnapshot] contains the first/last time, min/max BPM,
  /// and the rejection count at the time of the snapshot.
  HrBufferSnapshot window(DateTime start, DateTime end) {
    // Normalize to UTC.
    final startUtc = _normalizeToUtc(start);
    final endUtc = _normalizeToUtc(end);

    final firstHr = <int>[];
    final lastHr = <int>[];
    final firstTs = <DateTime>[];
    final lastTs = <DateTime>[];

    for (final sample in _samples) {
      final ts = _normalizeToUtc(sample.ts);
      if (ts.isAfter(startUtc) && ts.isBefore(endUtc)) {
        // Include samples exactly at the boundaries.
        // We'll check inclusive below.
      }
      // Check inclusive bounds.
      if (ts.isAfter(startUtc) || ts.isAtSameMomentAs(startUtc)) {
        if (ts.isBefore(endUtc) || ts.isAtSameMomentAs(endUtc)) {
          firstHr.add(sample.hr);
          firstTs.add(ts);
        }
      }
      if (ts.isBefore(endUtc) || ts.isAtSameMomentAs(endUtc)) {
        if (ts.isAfter(startUtc) || ts.isAtSameMomentAs(startUtc)) {
          lastHr.add(sample.hr);
          lastTs.add(ts);
        }
      }
    }

    // Simplify: return all samples in the window.
    // Actually, let's just return a snapshot with the samples that fall in window.
    final windowSamples = <HrSample>[];
    for (final sample in _samples) {
      final ts = _normalizeToUtc(sample.ts);
      if (ts.isAfter(startUtc) || ts.isAtSameMomentAs(startUtc)) {
        if (ts.isBefore(endUtc) || ts.isAtSameMomentAs(endUtc)) {
          windowSamples.add(sample);
        }
      }
    }

    final minHr = firstHr.isNotEmpty ? firstHr.reduce(min) : null;
    final maxHr = lastHr.isNotEmpty ? lastHr.reduce(max) : null;
    final firstTsVal = firstTs.isNotEmpty ? firstTs.reduce(min) : null;
    final lastTsVal = lastTsVal.isNotEmpty ? lastTsVal.reduce(max) : null;

    return HrBufferSnapshot(
      samples: windowSamples,
      firstHr: minHr,
      lastHr: maxHr,
      firstTs: firstTsVal,
      lastTs: lastTsVal,
      rejectionCount: _rejectionCount,
    );
  }

  /// Clear all samples and reset the rejection count.
  void reset() {
    _samples.clear();
    _rejectionCount = 0;
  }

  /// Normalize a [DateTime] to UTC, returning an aware UTC [DateTime].
  DateTime _normalizeToUtc(DateTime ts) {
    // If the timestamp is already UTC (no offset), keep it.
    // If it has an offset, convert to UTC.
    if (ts.timeZoneName == 'UTC' || ts.offset == 0) {
      return ts;
    }
    return ts.toUtc();
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