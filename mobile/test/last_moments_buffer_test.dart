import 'package:flutter_test/flutter_test.dart';
import 'package:sahyog_mobile/core/buffer/last_moments_buffer.dart';
import 'package:sahyog_mobile/features/monitoring/domain/hr_sample.dart';

void main() {
  group('LastMomentsBuffer', () {
    late LastMomentsBuffer buffer;

    setUp(() {
      buffer = LastMomentsBuffer();
    });

    group('add', () {
      test('first sample accepted unconditionally', () {
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 72,
        ));
        expect(buffer.sampleCount, equals(1));
      });

      test('duplicate timestamp rejected', () {
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 72,
        ));
        // Adding same timestamp again should be rejected
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 72,
        ));
        expect(buffer.rejectionCount, equals(1));
        expect(buffer.sampleCount, equals(1));
      });

      test('out-of-order timestamp rejected', () {
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 72,
        ));
        // Adding older timestamp should be rejected
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 9, 0, 0),
          hr: 60,
        ));
        expect(buffer.rejectionCount, equals(1));
        expect(buffer.sampleCount, equals(1));
      });

      test('newer timestamp accepted', () {
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 72,
        ));
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 1),
          hr: 75,
        ));
        expect(buffer.sampleCount, equals(2));
        expect(buffer.rejectionCount, equals(0));
      });

      test('retention window rejects old samples', () {
        buffer = LastMomentsBuffer(maxMs: 30000);
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 72,
        ));
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 1),
          hr: 75,
        ));
        // Add sample that is 31 seconds older than the latest - should be rejected as out-of-order
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 9, 59, 29),
          hr: 60,
        ));
        expect(buffer.sampleCount, equals(2));
      });
    });

    group('recent', () {
      test('returns samples in chronological order', () {
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 72,
        ));
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 1),
          hr: 75,
        ));
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 2),
          hr: 80,
        ));

        final recent = buffer.recent();
        expect(recent.length, equals(3));
        // Chronological: oldest first
        expect(recent[0].hr, equals(72));
        expect(recent[1].hr, equals(75));
        expect(recent[2].hr, equals(80));
      });

      test('recent with limit', () {
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 72,
        ));
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 1),
          hr: 75,
        ));

        final recent = buffer.recent(limit: 1);
        expect(recent.length, equals(1));
        expect(recent[0].hr, equals(75));
      });

      test('recent defaults to maxSamples', () {
        final buffer2 = LastMomentsBuffer(maxSamples: 10);
        buffer2.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 72,
        ));
        final recent = buffer2.recent();
        expect(recent.length, equals(1));
      });
    });

    group('window', () {
      test('snapshot includes correct samples', () {
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 72,
        ));
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 1),
          hr: 75,
        ));
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 2),
          hr: 80,
        ));

        final snapshot = buffer.window(
          DateTime.utc(2026, 11, 23, 10, 0, 0),
          DateTime.utc(2026, 11, 23, 10, 0, 1),
        );
        // Should include samples at 10:00:00 and 10:00:01
        expect(snapshot.samples.length, equals(2));
        expect(snapshot.firstHr, equals(72));
        expect(snapshot.lastHr, equals(75));
      });

      test('empty buffer snapshot', () {
        final emptyBuffer = LastMomentsBuffer();
        final snapshot = emptyBuffer.window(
          DateTime.utc(2026, 11, 23, 10, 0, 0),
          DateTime.utc(2026, 11, 23, 10, 0, 1),
        );
        expect(snapshot.samples, isEmpty);
        expect(snapshot.firstHr, isNull);
        expect(snapshot.lastHr, isNull);
      });
    });

    group('reset', () {
      test('clears all samples and resets rejection count', () {
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 72,
        ));
        // Add a duplicate to increment rejectionCount
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 72,
        ));
        expect(buffer.rejectionCount, equals(1));
        buffer.reset();
        expect(buffer.sampleCount, equals(0));
        expect(buffer.rejectionCount, equals(0));
      });
    });

    group('empty-buffer behavior', () {
      test('recent on empty buffer returns empty list', () {
        expect(buffer.recent().length, equals(0));
      });

      test('window on empty buffer returns safe snapshot', () {
        final snap = buffer.window(
          DateTime.utc(2026, 11, 23, 10, 0, 0),
          DateTime.utc(2026, 11, 23, 10, 0, 1),
        );
        expect(snap.samples, isEmpty);
        expect(snap.firstHr, isNull);
        expect(snap.lastHr, isNull);
      });
    });

    group('snapshot immutability', () {
      test('snapshot samples list cannot mutate internal buffer', () {
        buffer.add(HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 72,
        ));
        final snapshot = buffer.recent();
        expect(
          () => (snapshot as dynamic).add(HrSample(
            ts: DateTime.utc(2026, 11, 23, 10, 0, 1),
            hr: 90,
          )),
          throwsUnsupportedError,
        );
        expect(buffer.sampleCount, equals(1));
      });
    });
  });
}
