import type {
  DashboardOverview,
  HealthReading,
  IncidentDetail,
  IncidentSummary,
  LocationSnapshot,
  NearbyHospitalsResponse,
} from '../api/types';

const NOW = Date.now();

export function timestamp(offsetSeconds: number): string {
  return new Date(NOW + offsetSeconds * 1000).toISOString();
}

export const SUBJECT_ID = 'a1b2c3d4-1111-4111-8111-111111111111';
export const INCIDENT_ID = 'b2c3d4e5-2222-4222-8222-222222222222';
export const DEMO_RUN_ID = 'c3d4e5f6-3333-4333-8333-333333333333';

export function reading(id: string, bpm: number, offsetSeconds: number, source = 'SIMULATED'): HealthReading {
  return {
    reading_id: id,
    subject_user_id: SUBJECT_ID,
    demo_run_id: DEMO_RUN_ID,
    source_kind: source,
    heart_rate_bpm: bpm,
    observed_at: timestamp(offsetSeconds),
    received_at: timestamp(offsetSeconds + 1),
    activity_context: 'RESTING',
    is_stale: false,
  };
}

export function normalOverview(): DashboardOverview {
  const recent = [
    reading('read-3', 76, -180),
    reading('read-2', 80, -120),
    reading('read-1', 78, -60),
  ];
  return {
    generated_at: timestamp(0),
    subject_user_id: SUBJECT_ID,
    monitoring: {
      status: 'MONITORING',
      data_source: 'SIMULATED',
      detection_status: 'NORMAL',
      latest_reading: recent[2],
      recent_readings: recent,
      stale_after_seconds: 300,
    },
    active_incidents: [],
    active_incident_count: 0,
    recent_incidents: [],
    latest_location: null,
  };
}

export function escalatedIncident(): IncidentSummary {
  return {
    incident_id: INCIDENT_ID,
    subject_user_id: SUBJECT_ID,
    demo_run_id: DEMO_RUN_ID,
    run_generation: 1,
    status: 'ESCALATED',
    created_at: timestamp(-300),
    updated_at: timestamp(-45),
    verification_deadline_at: timestamp(-80),
    resolved_at: null,
    anomaly_event: {
      anomaly_event_id: 'd4e5f6a7-4444-4444-8444-444444444444',
      detected_at: timestamp(-280),
      detector_result: 'SUSTAINED_TACHYCARDIA',
      severity: 'HIGH',
      explanation: 'Sustained heart rate above the configured demo threshold.',
      detector_version: 'demo-detector-1.0',
    },
    verification: {
      status: 'PENDING_VERIFICATION',
      pending: true,
      deadline_at: timestamp(-80),
      responses: [],
    },
    escalation_attempts: [
      {
        escalation_attempt_id: 'e5f6a7b8-5555-4555-8555-555555555555',
        trigger_reason: 'VERIFICATION_TIMEOUT',
        status: 'COMPLETED',
        started_at: timestamp(-70),
        completed_at: timestamp(-65),
        notifications: [
          {
            notification_attempt_id: 'f6a7b8c9-6666-4666-8666-666666666666',
            notification_type: 'SMS',
            recipient_reference: 'caregiver-demo-1',
            result: 'SIMULATED',
            attempted_at: timestamp(-68),
          },
        ],
      },
    ],
    location: {
      location_snapshot_id: 'e5f6a7b8-4444-4444-8444-444444444444',
      subject_user_id: SUBJECT_ID,
      incident_id: INCIDENT_ID,
      demo_run_id: DEMO_RUN_ID,
      latitude: 18.5204,
      longitude: 73.8567,
      accuracy_meters: 12,
      captured_at: timestamp(-240),
      received_at: timestamp(-239),
      source_kind: 'SIMULATED',
      is_stale: false,
      stale_after_seconds: 300,
    },
  };
}

export function escalatedOverview(): DashboardOverview {
  const incident = escalatedIncident();
  return {
    generated_at: timestamp(0),
    subject_user_id: SUBJECT_ID,
    monitoring: {
      status: 'MONITORING',
      data_source: 'SIMULATED',
      detection_status: 'ANOMALY_DETECTED',
      latest_reading: reading('read-5', 126, -40),
      recent_readings: [
        reading('read-5', 126, -40),
        reading('read-4', 118, -100),
        reading('read-3', 76, -180),
      ],
      stale_after_seconds: 300,
    },
    active_incidents: [incident],
    active_incident_count: 1,
    recent_incidents: [incident],
    latest_location: incident.location,
  };
}

export function escalatedDetail(): IncidentDetail {
  return {
    ...escalatedIncident(),
    evidence: [],
    timeline: [
      {
        timeline_event_id: 't-1',
        event_type: 'INCIDENT_CREATED',
        occurred_at: timestamp(-300),
        details: 'Backend created the incident from the triggering anomaly event.',
      },
      {
        timeline_event_id: 't-2',
        event_type: 'VERIFICATION_STARTED',
        occurred_at: timestamp(-290),
        details: 'The person was asked to confirm they are okay.',
      },
      {
        timeline_event_id: 't-3',
        event_type: 'VERIFICATION_TIMEOUT',
        occurred_at: timestamp(-80),
        details: 'The verification window expired with no response.',
      },
      {
        timeline_event_id: 't-4',
        event_type: 'ESCALATION_RECORDED',
        occurred_at: timestamp(-65),
        details: 'Demo notification recorded. No real delivery.',
      },
    ],
  };
}

export function falseAlarmIncident(): IncidentSummary {
  return {
    incident_id: 'f1f2f3f4-7777-4777-8777-777777777777',
    subject_user_id: SUBJECT_ID,
    demo_run_id: DEMO_RUN_ID,
    run_generation: 1,
    status: 'RESOLVED_FALSE_ALARM',
    created_at: timestamp(-240),
    updated_at: timestamp(-90),
    verification_deadline_at: timestamp(-30),
    resolved_at: timestamp(-90),
    anomaly_event: {
      anomaly_event_id: 'a7b8c9d0-8888-4888-8888-888888888888',
      detected_at: timestamp(-230),
      detector_result: 'SUSTAINED_TACHYCARDIA',
      severity: 'MEDIUM',
      explanation: 'Heart rate exceeded the configured demo threshold for the required duration.',
      detector_version: 'demo-detector-1.0',
    },
    verification: {
      status: 'RESOLVED_FALSE_ALARM',
      pending: false,
      deadline_at: timestamp(-30),
      responses: [
        {
          verification_response_id: 'response-1',
          response_value: 'I_AM_OK',
          responded_at: timestamp(-95),
        },
      ],
    },
    escalation_attempts: [],
    location: null,
  };
}

export function falseAlarmOverview(): DashboardOverview {
  const incident = falseAlarmIncident();
  return {
    generated_at: timestamp(0),
    subject_user_id: SUBJECT_ID,
    monitoring: {
      status: 'MONITORING',
      data_source: 'SIMULATED',
      detection_status: 'NORMAL',
      latest_reading: reading('read-6', 74, -30),
      recent_readings: [reading('read-6', 74, -30), reading('read-5', 120, -120)],
      stale_after_seconds: 300,
    },
    active_incidents: [],
    active_incident_count: 0,
    recent_incidents: [incident],
    latest_location: null,
  };
}

export function falseAlarmDetail(): IncidentDetail {
  return {
    ...falseAlarmIncident(),
    timeline: [
      {
        timeline_event_id: 'ff-1',
        event_type: 'ANOMALY_DETECTED',
        occurred_at: timestamp(-230),
      },
      {
        timeline_event_id: 'ff-2',
        event_type: 'VERIFICATION_STARTED',
        occurred_at: timestamp(-220),
      },
      {
        timeline_event_id: 'ff-3',
        event_type: 'I_AM_OK_CONFIRMED',
        occurred_at: timestamp(-95),
        details: 'The person confirmed they are okay.',
      },
      {
        timeline_event_id: 'ff-4',
        event_type: 'PENDING_ESCALATION_CANCELLED',
        occurred_at: timestamp(-95),
      },
      {
        timeline_event_id: 'ff-5',
        event_type: 'FALSE_ALARM_RESOLVED',
        occurred_at: timestamp(-90),
      },
    ],
  };
}

export function pendingIncident(): IncidentSummary {
  return {
    incident_id: 'aa11bb22-9999-4999-8999-999999999999',
    subject_user_id: SUBJECT_ID,
    demo_run_id: DEMO_RUN_ID,
    run_generation: 1,
    status: 'PENDING_VERIFICATION',
    created_at: timestamp(-60),
    updated_at: timestamp(-55),
    verification_deadline_at: timestamp(30),
    resolved_at: null,
    anomaly_event: {
      anomaly_event_id: 'bb22cc33-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      detected_at: timestamp(-70),
      detector_result: 'SUSTAINED_TACHYCARDIA',
      severity: 'MEDIUM',
      explanation: 'Sustained elevation detected by the demo detector.',
    },
    verification: {
      status: 'PENDING_VERIFICATION',
      pending: true,
      deadline_at: timestamp(30),
      responses: [],
    },
    escalation_attempts: [],
    location: null,
  };
}

export function pendingOverview(): DashboardOverview {
  const incident = pendingIncident();
  return {
    generated_at: timestamp(0),
    subject_user_id: SUBJECT_ID,
    monitoring: {
      status: 'MONITORING',
      data_source: 'SIMULATED',
      detection_status: 'ANOMALY_DETECTED',
      latest_reading: reading('read-p1', 132, -20),
      recent_readings: [reading('read-p1', 132, -20)],
      stale_after_seconds: 300,
    },
    active_incidents: [incident],
    active_incident_count: 1,
    recent_incidents: [incident],
    latest_location: null,
  };
}

export function pendingDetail(): IncidentDetail {
  return {
    ...pendingIncident(),
    timeline: [
      {
        timeline_event_id: 'p-1',
        event_type: 'ANOMALY_DETECTED',
        occurred_at: timestamp(-70),
      },
      {
        timeline_event_id: 'p-2',
        event_type: 'VERIFICATION_STARTED',
        occurred_at: timestamp(-60),
      },
    ],
  };
}

export function locationSnapshot(): LocationSnapshot {
  return {
    location_snapshot_id: 'e5f6a7b8-4444-4444-8444-444444444444',
    subject_user_id: SUBJECT_ID,
    incident_id: null,
    demo_run_id: DEMO_RUN_ID,
    latitude: 18.5204,
    longitude: 73.8567,
    accuracy_meters: 9,
    captured_at: timestamp(-30),
    received_at: timestamp(-29),
    source_kind: 'SIMULATED',
    is_stale: false,
    stale_after_seconds: 300,
  };
}

export function hospitalsResponse(): NearbyHospitalsResponse {
  return {
    provider: 'SEEDED_DEMO_DIRECTORY',
    disclaimer:
      'Seeded demo directory only. No hospital has been contacted, is confirmed available, or has accepted an incident.',
    generated_at: timestamp(0),
    hospitals: [
      {
        hospital_id: 'hospital-1',
        name: 'SAHYOG Demo General Hospital',
        address: 'Demo Road, Pune',
        latitude: 18.528,
        longitude: 73.86,
        distance_meters: 1200,
        source_kind: 'SEEDED_DEMO',
      },
      {
        hospital_id: 'hospital-2',
        name: 'Demo Community Care Centre',
        address: 'Sample Street, Pune',
        latitude: 18.54,
        longitude: 73.88,
        distance_meters: 3400,
        source_kind: 'SEEDED_DEMO',
      },
    ],
  };
}
