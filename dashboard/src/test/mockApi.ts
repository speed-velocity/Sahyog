import { vi } from 'vitest';

export interface MockApiState {
  overview?: unknown;
  incidents?: unknown[];
  detail?: unknown;
  detailById?: Record<string, unknown>;
  hospitals?: unknown;
  location?: unknown;
  authorizedSubjects?: unknown[];
  overviewBySubject?: Record<string, unknown>;
  incidentsBySubject?: Record<string, unknown[]>;
  locationBySubject?: Record<string, unknown>;
  loginStatus?: number;
  loginErrorBody?: unknown;
  authorizationsStatus?: number;
  authorizationsErrorBody?: unknown;
  overviewStatus?: number;
  incidentsStatus?: number;
  detailStatus?: number;
  hospitalsStatus?: number;
  locationStatus?: number;
  overviewErrorBody?: unknown;
  incidentsErrorBody?: unknown;
  detailErrorBody?: unknown;
  hospitalsErrorBody?: unknown;
}

function respond(body: unknown, status = 200, errorBody?: unknown): Response {
  const payload = status >= 400 ? (errorBody ?? { error: { code: 'MOCK_ERROR', message: 'Mock API error' } }) : body;
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export function installDashboardMock(initialState: MockApiState) {
  let state = initialState;

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const raw =
      typeof input === 'string'
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    const url = new URL(raw, 'http://dashboard.test');
    const path = url.pathname;
    const method = init?.method ?? 'GET';
    const authHeader = new Headers(init?.headers).get('Authorization') ?? '';
    const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7) : '';

    if (path.endsWith('/auth/token') && method === 'POST') {
      const form = new URLSearchParams(String(init?.body ?? ''));
      if (!form.get('username') || !form.get('password')) {
        return respond(null, 422, { detail: 'Username and password are required.' });
      }
      if ((state.loginStatus ?? 200) >= 400) {
        return respond(null, state.loginStatus, state.loginErrorBody ?? { detail: 'Incorrect username or password' });
      }
      return respond({ access_token: 'mock-jwt-token-for-testing', token_type: 'bearer' });
    }

    if (path.endsWith('/authorizations/me')) {
      if (token !== 'mock-jwt-token-for-testing') {
        return respond(null, token ? 403 : 401, { detail: token ? 'Only caregivers may list authorized subjects' : 'Could not validate credentials' });
      }
      return respond({
        authorized_subjects: state.authorizedSubjects ?? [
          {
            subject_user_id: 'a1b2c3d4-1111-4111-8111-111111111111',
            granted_at: '2026-11-28T10:00:00Z',
            revoked_at: null,
          },
        ],
      }, state.authorizationsStatus, state.authorizationsErrorBody);
    }

    if (path.startsWith('/api/v1/') && path !== '/api/v1/auth/token' && token !== 'mock-jwt-token-for-testing') {
      return respond(null, 401, { detail: 'Could not validate credentials' });
    }

    const authorizedSubjectIds = (state.authorizedSubjects ?? [
      { subject_user_id: 'a1b2c3d4-1111-4111-8111-111111111111' },
    ]).map((subject) => (subject as { subject_user_id: string }).subject_user_id);

    if (path.endsWith('/dashboard/overview')) {
      const subjectId = url.searchParams.get('subject_user_id');
      if (!subjectId || !authorizedSubjectIds.includes(subjectId)) return respond(null, 403, { detail: 'Dashboard access denied' });
      return respond(state.overviewBySubject?.[subjectId] ?? state.overview, state.overviewStatus, state.overviewErrorBody);
    }
    if (path.endsWith('/incidents')) {
      const subjectId = url.searchParams.get('subject_user_id');
      if (!subjectId || !authorizedSubjectIds.includes(subjectId)) return respond(null, 403, { detail: 'Incident access denied' });
      const incidents = state.incidentsBySubject?.[subjectId] ?? (state.incidents ?? []).filter(
        (incident) => (incident as { subject_user_id?: string }).subject_user_id === subjectId,
      );
      return respond(incidents, state.incidentsStatus, state.incidentsErrorBody);
    }
    if (/\/incidents\/[^/]+$/.test(path)) {
      const incidentId = path.split('/').at(-1) ?? '';
      const incident = state.detailById?.[incidentId] ?? state.detail;
      if (incident && (incident as { incident_id?: string }).incident_id !== incidentId) {
        return respond(null, 404, { detail: 'Incident not found' });
      }
      if (incident && (incident as { subject_user_id?: string }).subject_user_id &&
          !authorizedSubjectIds.includes((incident as { subject_user_id: string }).subject_user_id)) {
        return respond(null, 403, { detail: 'Incident access denied' });
      }
      return respond(incident, state.detailStatus ?? (incident === undefined ? 404 : 200), state.detailErrorBody);
    }
    if (path.endsWith('/hospitals/nearby')) {
      return respond(state.hospitals, state.hospitalsStatus, state.hospitalsErrorBody);
    }
    if (path.endsWith('/location/latest')) {
      const subjectId = url.searchParams.get('subject_user_id');
      if (!subjectId || !authorizedSubjectIds.includes(subjectId)) return respond(null, 403, { error: { code: 'LOCATION_ACCESS_DENIED', message: 'Location access denied.' } });
      const location = state.locationBySubject?.[subjectId] ?? state.location;
      const status = state.locationStatus ?? (location === undefined ? 404 : 200);
      return respond(
        location,
        status,
        { error: { code: 'NO_LOCATION_RECORDED', message: 'No location snapshot recorded.' } },
      );
    }

    return respond(null, 404, { error: { code: 'NOT_FOUND', message: 'Not found in dashboard test.' } });
  });

  vi.stubGlobal('fetch', fetchMock);

  return {
    fetchMock,
    update(partial: Partial<MockApiState>) {
      state = { ...state, ...partial };
    },
  };
}
