/// SimScenario — the three approved demo scenario identifiers.
///
/// These are the exact scenario strings sent to the backend
/// `POST /api/v1/demo/runs` endpoint. All three scenarios share the same
/// application pipeline; they differ only in their input data and expected
/// outcome.
///
/// - `normal`: NORMAL — no anomaly, no incident, no verification, no escalation.
/// - `trueAnomaly`: TRUE_ANOMALY — sustained abnormal pattern triggers
///   detection, verification, and (if no response) escalation.
/// - `falseAlarm`: FALSE_ALARM — same abnormal pattern triggers detection,
///   but the user subsequently confirms `I_AM_OK`, allowing the backend to
///   resolve it as `RESOLVED_FALSE_ALARM`.
library;
enum SimScenario {
  /// NORMAL — no emergency, no anomaly detected.
  normal,

  /// TRUE_ANOMALY — sustained abnormal pattern; detection → verification → escalation.
  trueAnomaly,

  /// FALSE_ALARM — same abnormal pattern as trueAnomaly, but user confirms
  /// I_AM_OK → RESOLVED_FALSE_ALARM.
  falseAlarm;

  @override
  String toString() {
    switch (this) {
      case SimScenario.normal:
        return 'NORMAL';
      case SimScenario.trueAnomaly:
        return 'TRUE_ANOMALY';
      case SimScenario.falseAlarm:
        return 'FALSE_ALARM';
    }
  }
}