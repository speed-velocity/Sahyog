import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import App from '../App';
import {
  INCIDENT_ID,
  SECOND_SUBJECT_ID,
  SUBJECT_ID,
  hospitalsResponse,
  incidentResponse,
  locationSnapshot,
  overviewResponse,
  timestamp,
} from './apiFixtures';
import { installDashboardMock } from './mockApi';

const authorized = (subjectId: string) => ({
  subject_user_id: subjectId,
  granted_at: timestamp(-1000),
  revoked_at: null,
});
beforeEach(() => {
  sessionStorage.setItem('sahyog_token', 'mock-jwt-token-for-testing');
});

function requestUrls(mock: ReturnType<typeof installDashboardMock>) {
  return mock.fetchMock.mock.calls.map(([input]) => String(input));
}

async function navigate(user: ReturnType<typeof userEvent.setup>, label: RegExp) {
  await user.click(screen.getByRole('button', { name: label }));
}

describe('SAHYOG dashboard integration against backend response contracts', () => {
  it('does not request protected resources without a session token', () => {
    sessionStorage.removeItem('sahyog_token');
    const mock = installDashboardMock({});
    render(<App />);

    expect(screen.getByRole('heading', { name: 'Caregiver Login' })).toBeInTheDocument();
    expect(mock.fetchMock).not.toHaveBeenCalled();
  });

  it('posts URL-encoded credentials to the backend token route and stores its token', async () => {
    sessionStorage.removeItem('sahyog_token');
    const user = userEvent.setup();
    const mock = installDashboardMock({ overview: overviewResponse(), incidents: [] });
    render(<App />);

    await user.type(screen.getByLabelText('Username'), 'test-caregiver');
    await user.type(screen.getByLabelText('Password'), 'test-password');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect((await screen.findAllByText('78 bpm')).length).toBeGreaterThan(0);
    expect(sessionStorage.getItem('sahyog_token')).toBe('mock-jwt-token-for-testing');
    const loginRequest = mock.fetchMock.mock.calls.find(([input]) => String(input).endsWith('/auth/token'));
    expect(loginRequest?.[1]?.method).toBe('POST');
    expect(loginRequest?.[1]?.headers).toMatchObject({ 'Content-Type': 'application/x-www-form-urlencoded' });
    expect(String(loginRequest?.[1]?.body)).toContain('username=test-caregiver');
  });

  it('shows backend login errors', async () => {
    sessionStorage.removeItem('sahyog_token');
    const user = userEvent.setup();
    installDashboardMock({ loginStatus: 401, loginErrorBody: { detail: 'Incorrect username or password' } });
    render(<App />);

    await user.type(screen.getByLabelText('Username'), 'wrong-user');
    await user.type(screen.getByLabelText('Password'), 'wrong-password');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect(await screen.findByText('Incorrect username or password')).toBeInTheDocument();
    expect(sessionStorage.getItem('sahyog_token')).toBeNull();
  });

  it('sends the stored token as Bearer authorization to subject discovery', async () => {
    const mock = installDashboardMock({ overview: overviewResponse(), incidents: [] });
    render(<App />);

    expect((await screen.findAllByText('78 bpm')).length).toBeGreaterThan(0);
    const authorizationCall = mock.fetchMock.mock.calls.find(([input]) => String(input).endsWith('/authorizations/me'));
    expect(new Headers(authorizationCall?.[1]?.headers).get('Authorization')).toBe('Bearer mock-jwt-token-for-testing');
  });

  it('handles zero authorized subjects without starting overview, incident, or detail polling', async () => {
    const mock = installDashboardMock({ authorizedSubjects: [], overview: overviewResponse(), incidents: [] });
    render(<App />);

    expect(await screen.findByText('No subjects are authorized for this caregiver account.')).toBeInTheDocument();
    expect(requestUrls(mock).some((url) => url.includes('/dashboard/overview'))).toBe(false);
    expect(requestUrls(mock).some((url) => /\/incidents(?:\?|\/)/.test(new URL(url).pathname + new URL(url).search))).toBe(false);
  });

  it('automatically selects one authorized subject and sends the subject query parameter', async () => {
    const mock = installDashboardMock({ overview: overviewResponse(), incidents: [] });
    render(<App />);

    expect((await screen.findAllByText('78 bpm')).length).toBeGreaterThan(0);
    expect(screen.queryByRole('combobox', { name: 'Select monitored subject' })).not.toBeInTheDocument();
    expect(requestUrls(mock).some((url) => url.includes(`subject_user_id=${SUBJECT_ID}`))).toBe(true);
  });

  it('shows a subject discovery error and retry action without starting data polling', async () => {
    const mock = installDashboardMock({
      authorizationsStatus: 503,
      authorizationsErrorBody: { detail: 'Authorization service offline.' },
    });
    render(<App />);

    expect(await screen.findByText(/Authorization service offline/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry subject discovery' })).toBeInTheDocument();
    expect(requestUrls(mock).some((url) => url.includes('/dashboard/overview'))).toBe(false);
    expect(requestUrls(mock).some((url) => new URL(url).pathname.endsWith('/incidents'))).toBe(false);
  });

  it('retries subject discovery and starts monitoring after discovery succeeds', async () => {
    const user = userEvent.setup();
    const mock = installDashboardMock({
      authorizationsStatus: 503,
      authorizationsErrorBody: { detail: 'Authorization service offline.' },
    });
    render(<App />);

    expect(await screen.findByText(/Authorization service offline/)).toBeInTheDocument();
    mock.update({ authorizationsStatus: undefined, overview: overviewResponse(), incidents: [] });
    await user.click(screen.getByRole('button', { name: 'Retry subject discovery' }));

    expect((await screen.findAllByText('78 bpm')).length).toBeGreaterThan(0);
    expect(requestUrls(mock).filter((url) => url.endsWith('/authorizations/me'))).toHaveLength(2);
  });

  it('shows an authorization error for a non-caregiver session', async () => {
    sessionStorage.setItem('sahyog_token', 'mock-subject-token');
    const mock = installDashboardMock({});
    render(<App />);

    expect(await screen.findByText(/Only caregivers may list authorized subjects/)).toBeInTheDocument();
    expect(requestUrls(mock).some((url) => url.includes('/dashboard/overview'))).toBe(false);
  });

  it('does not expose subject UUIDs in the visible selector and suppresses old subject data on switch', async () => {
    const user = userEvent.setup();
    const firstIncident = incidentResponse('ESCALATED', SUBJECT_ID, INCIDENT_ID);
    const secondIncidentId = 'c3d4e5f6-3333-4333-8333-333333333333';
    const mock = installDashboardMock({
      authorizedSubjects: [authorized(SUBJECT_ID), authorized(SECOND_SUBJECT_ID)],
      overviewBySubject: {
        [SUBJECT_ID]: overviewResponse(SUBJECT_ID, { activeIncident: INCIDENT_ID }),
        [SECOND_SUBJECT_ID]: overviewResponse(SECOND_SUBJECT_ID, { bpm: 91 }),
      },
      incidentsBySubject: {
        [SUBJECT_ID]: [firstIncident],
        [SECOND_SUBJECT_ID]: [incidentResponse('RESOLVED_FALSE_ALARM', SECOND_SUBJECT_ID, secondIncidentId)],
      },
      detail: firstIncident,
    });
    render(<App />);

    const selector = await screen.findByRole('combobox', { name: 'Select monitored subject' });
    expect(within(selector).getByRole('option', { name: 'Authorized subject 1' })).toBeInTheDocument();
    expect(selector.textContent).not.toContain(SUBJECT_ID);
    await user.selectOptions(selector, SUBJECT_ID);
    expect((await screen.findAllByText('78 bpm')).length).toBeGreaterThan(0);

    await user.selectOptions(selector, SECOND_SUBJECT_ID);
    expect((await screen.findAllByText('91 bpm')).length).toBeGreaterThan(0);
    expect(screen.queryByText('78 bpm')).not.toBeInTheDocument();
    expect(screen.queryByText(INCIDENT_ID)).not.toBeInTheDocument();
    expect(requestUrls(mock).some((url) => url.includes(`subject_user_id=${SECOND_SUBJECT_ID}`))).toBe(true);
  });

  it('renders only status and timestamps returned by incident detail', async () => {
    const user = userEvent.setup();
    const incident = incidentResponse('ESCALATED');
    installDashboardMock({
      overview: overviewResponse(SUBJECT_ID, { activeIncident: incident.incident_id }),
      incidents: [incident],
      detail: incident,
    });
    render(<App />);

    await screen.findAllByText('78 bpm');
    await navigate(user, /^Incidents/);
    expect(await screen.findByRole('heading', { name: 'Incident timeline' })).toBeInTheDocument();
    expect(screen.getByText(/does not include verification records/)).toBeInTheDocument();
    expect(screen.queryByText(/Recipient:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Explicit confirmation recorded/)).not.toBeInTheDocument();
  });

  it('handles the flat backend overview and does not invent detector, history, or freshness fields', async () => {
    const user = userEvent.setup();
    installDashboardMock({ overview: overviewResponse(), incidents: [] });
    render(<App />);

    expect((await screen.findAllByText('78 bpm')).length).toBeGreaterThan(0);
    expect(screen.getByText('Monitoring status')).toBeInTheDocument();
    expect(screen.getByText('No active incident reported.')).toBeInTheDocument();
    expect(screen.queryByText(/ANOMALY_DETECTED/)).not.toBeInTheDocument();

    await navigate(user, /^Health monitoring/);
    expect(screen.getByText(/no reading-history endpoint is available/i)).toBeInTheDocument();
    expect(screen.getByText(/Freshness not reported/)).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('keeps location and hospital data scoped to the selected subject', async () => {
    const user = userEvent.setup();
    const secondLocation = {
      ...locationSnapshot(SECOND_SUBJECT_ID),
      latitude: 19.076,
      longitude: 72.8777,
    };
    installDashboardMock({
      authorizedSubjects: [authorized(SUBJECT_ID), authorized(SECOND_SUBJECT_ID)],
      overviewBySubject: {
        [SUBJECT_ID]: overviewResponse(SUBJECT_ID),
        [SECOND_SUBJECT_ID]: overviewResponse(SECOND_SUBJECT_ID, { bpm: 91 }),
      },
      incidentsBySubject: { [SUBJECT_ID]: [], [SECOND_SUBJECT_ID]: [] },
      locationBySubject: {
        [SUBJECT_ID]: locationSnapshot(SUBJECT_ID),
        [SECOND_SUBJECT_ID]: secondLocation,
      },
      hospitals: hospitalsResponse(),
    });
    render(<App />);

    const selector = await screen.findByRole('combobox', { name: 'Select monitored subject' });
    await user.selectOptions(selector, SUBJECT_ID);
    await user.click(screen.getByRole('button', { name: /^Location & support/ }));
    expect(await screen.findByText('18.52040, 73.85670')).toBeInTheDocument();

    await user.selectOptions(selector, SECOND_SUBJECT_ID);
    expect(await screen.findByText('19.07600, 72.87770')).toBeInTheDocument();
    expect(screen.queryByText('18.52040, 73.85670')).not.toBeInTheDocument();
  });

  it('does not show a location or request hospitals when the backend has no snapshot', async () => {
    const user = userEvent.setup();
    const mock = installDashboardMock({ overview: overviewResponse(), incidents: [] });
    render(<App />);

    await screen.findAllByText('78 bpm');
    await navigate(user, /^Location & support/);
    expect(await screen.findByText('Location unavailable')).toBeInTheDocument();
    expect(screen.getByText('Hospital lookup unavailable')).toBeInTheDocument();
    expect(requestUrls(mock).some((url) => url.includes('/hospitals/nearby'))).toBe(false);
  });

  it('uses the backend hospital response and displays its disclaimer', async () => {
    const user = userEvent.setup();
    installDashboardMock({
      overview: overviewResponse(),
      incidents: [],
      location: locationSnapshot(),
      hospitals: hospitalsResponse(),
    });
    render(<App />);

    await screen.findAllByText('78 bpm');
    await navigate(user, /^Location & support/);
    expect(await screen.findByText('SAHYOG Demo General Hospital')).toBeInTheDocument();
    expect(screen.getByText('1.2 km')).toBeInTheDocument();
    expect(screen.getByText(/availability is not confirmed/)).toBeInTheDocument();
  });

  it('stops protected polling after logout and clears all subject-specific state', async () => {
    const user = userEvent.setup();
    const mock = installDashboardMock({
      overview: overviewResponse(SUBJECT_ID, { activeIncident: INCIDENT_ID }),
      incidents: [incidentResponse('ESCALATED')],
      detail: incidentResponse('ESCALATED'),
      location: locationSnapshot(),
    });
    render(<App />);

    expect((await screen.findAllByText('78 bpm')).length).toBeGreaterThan(0);
    const beforeLogout = requestUrls(mock).length;
    await user.click(screen.getByRole('button', { name: 'Log out' }));
    expect(sessionStorage.getItem('sahyog_token')).toBeNull();
    expect(screen.getByRole('heading', { name: 'Caregiver Login' })).toBeInTheDocument();
    expect(screen.queryByText('78 bpm')).not.toBeInTheDocument();
    expect(screen.queryByText(INCIDENT_ID)).not.toBeInTheDocument();
    await waitFor(() => expect(requestUrls(mock).length).toBe(beforeLogout));
  });

  it('rejects a malformed overview rather than interpreting a different response shape', async () => {
    const mock = installDashboardMock({ overview: { overview: overviewResponse() }, incidents: [] });
    render(<App />);

    expect(await screen.findByText(/latest reading response was not readable/i)).toBeInTheDocument();
    expect(requestUrls(mock).some((url) => url.includes(`subject_user_id=${SUBJECT_ID}`))).toBe(true);
  });
});
