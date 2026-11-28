import 'package:flutter_test/flutter_test.dart';
import 'package:sahyog_mobile/features/monitoring/domain/hr_sample.dart';

void main() {
  group('HrSample', () {
    test('valid BPM accepted', () {
      final sample = HrSample(
        ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
        hr: 72,
      );
      expect(sample.hr, equals(72));
      expect(sample.ts, equals(DateTime.utc(2026, 11, 23, 10, 0, 0)));
    });

    test('invalid BPM too low throws', () {
      expect(
        () => HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 15,
        ),
        throwsArgumentError,
      );
    });

    test('invalid BPM too high throws', () {
      expect(
        () => HrSample(
          ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
          hr: 260,
        ),
        throwsArgumentError,
      );
    });

    test('UTC timestamp behavior', () {
      final sample = HrSample(
        ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
        hr: 72,
      );
      // Verify the timestamp is UTC
      expect(sample.ts.timeZoneName, isNotEmpty);
      expect(sample.ts.isUtc, isTrue);
    });

    test('immutability - original remains unchanged after copyWith', () {
      final sample = HrSample(
        ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
        hr: 72,
      );
      final copy = sample.copyWith(
        ts: DateTime.utc(2026, 11, 23, 11, 0, 0),
        hr: 80,
      );
      expect(sample.ts, equals(DateTime.utc(2026, 11, 23, 10, 0, 0)));
      expect(sample.hr, equals(72));
      expect(copy.ts, equals(DateTime.utc(2026, 11, 23, 11, 0, 0)));
      expect(copy.hr, equals(80));
    });

    test('copyWith creates a new instance', () {
      final original = HrSample(
        ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
        hr: 72,
      );
      final copy = original.copyWith(
        ts: DateTime.utc(2026, 11, 23, 11, 0, 0),
      );
      expect(copy.hr, equals(72)); // unchanged
      expect(copy.ts, equals(DateTime.utc(2026, 11, 23, 11, 0, 0))); // changed
      expect(copy, isNot(equals(original))); // different object
    });

    test('operator == and hashCode consistency', () {
      final a = HrSample(
        ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
        hr: 72,
      );
      final b = HrSample(
        ts: DateTime.utc(2026, 11, 23, 10, 0, 0),
        hr: 72,
      );
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });
}
