import { vi } from 'vitest';

export interface MockApiState {
  overview?: unknown;
  incidents?: unknown;
  detail?: unknown;
  hospitals?: unknown;
  location?: unknown;
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

  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const raw =
      typeof input === 'string'
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    const url = new URL(raw, 'http://dashboard.test');
    const path = url.pathname;

    if (path.endsWith('/dashboard/overview')) {
      return respond(state.overview, state.overviewStatus, state.overviewErrorBody);
    }
    if (path.endsWith('/incidents')) {
      return respond(state.incidents, state.incidentsStatus, state.incidentsErrorBody);
    }
    if (/\/incidents\/[^/]+$/.test(path)) {
      return respond(state.detail, state.detailStatus, state.detailErrorBody);
    }
    if (path.endsWith('/hospitals/nearby')) {
      return respond(state.hospitals, state.hospitalsStatus, state.hospitalsErrorBody);
    }
    if (path.endsWith('/location/latest')) {
      return respond(
        state.location,
        state.locationStatus ?? (state.location === undefined ? 404 : 200),
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
