import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import App from '../App';
import {
  escalatedDetail,
  escalatedIncident,
  escalatedOverview,
  falseAlarmDetail,
  falseAlarmIncident,
  falseAlarmOverview,
  hospitalsResponse,
  locationSnapshot,
  normalOverview,
  pendingDetail,
  pendingIncident,
  pendingOverview,
  timestamp,
} from './fixtures';
import { installDashboardMock } from './mockApi';

async function openView(user: ReturnType<typeof userEvent.setup>, name: RegExp) {
  await user.click(screen.getByRole('button', { name }));
}

describe('SAHYOG caregiver dashboard', () => {
  it('renders normal operation with simulated reading data and no incidents', async () => {
    installDashboardMock({ overview: normalOverview(), incidents: { incidents: [] } });
    render(<App />);

    expect(await screen.findByText(/Normal operation/)).toBeInTheDocument();
    expect(screen.getAllByText('Monitored person').length).toBeGreaterThan(0);
    expect(await screen.findByText('No recent incidents')).toBeInTheDocument();
    expect(screen.getAllByText(/Simulated/).length).toBeGreaterThan(0);
    expect(screen.getByText('Active incidents')).toBeInTheDocument();
  });

  it('renders the reading history chart and table in health monitoring', async () => {
    const user = userEvent.setup();
    installDashboardMock({ overview: normalOverview(), incidents: { incidents: [] } });
    render(<App />);

    await screen.findByText(/Normal operation/);
    await openView(user, /^Health monitoring/);

    const chart = await screen.findByRole('img', { name: /readings between/i });
    expect(chart).toBeInTheDocument();

    const table = screen.getByRole('table');
    expect(within(table).getAllByText(/bpm/).length).toBeGreaterThan(0);
    expect(screen.getByText('Heart-rate trend')).toBeInTheDocument();
    expect(screen.getAllByText('Reading history').length).toBeGreaterThan(0);
    expect(screen.queryByText(/Only one reading was returned/)).not.toBeInTheDocument();
  });

  it('renders an escalated incident with pending verification and a simulated notification', async () => {
    const user = userEvent.setup();
    installDashboardMock({
      overview: escalatedOverview(),
      incidents: { incidents: [escalatedIncident()] },
      detail: escalatedDetail(),
      location: locationSnapshot(),
      hospitals: hospitalsResponse(),
    });
    render(<App />);

    expect(await screen.findByText(/Escalated incident reported by the backend/)).toBeInTheDocument();
    await openView(user, /^Incidents/);

    expect(await screen.findByRole('heading', { name: 'Incident timeline' })).toBeInTheDocument();
    expect(screen.getAllByText('Escalated').length).toBeGreaterThan(0);
    expect(screen.getByText(/No response recorded/)).toBeInTheDocument();
    expect(
      screen.getByText('Simulated notification — no real message or call was delivered.'),
    ).toBeInTheDocument();
    expect(screen.getByText(/Recipient: caregiver-demo-1/)).toBeInTheDocument();
    expect(screen.getAllByText(/Verification timeout/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText('High').length).toBeGreaterThan(0);
  });

  it('renders a false-alarm resolution with an explicit confirmation and no escalation', async () => {
    const user = userEvent.setup();
    installDashboardMock({
      overview: falseAlarmOverview(),
      incidents: { incidents: [falseAlarmIncident()] },
      detail: falseAlarmDetail(),
    });
    render(<App />);

    await screen.findByText(/Normal operation/);
    await openView(user, /^Incidents/);

    expect(await screen.findByRole('heading', { name: 'Incident timeline' })).toBeInTheDocument();
    expect(screen.getAllByText('False alarm resolved').length).toBeGreaterThan(0);
    expect(screen.getByText(/Explicit confirmation recorded/)).toBeInTheDocument();
    expect(screen.getByText("I'm okay")).toBeInTheDocument();
    expect(screen.getByText(/No escalation attempts have been recorded/)).toBeInTheDocument();
    expect(screen.queryByText(/No response recorded/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Escalated incident reported by the backend/)).not.toBeInTheDocument();
  });

  it('distinguishes verification pending from an explicit confirmation', async () => {
    const user = userEvent.setup();
    installDashboardMock({
      overview: pendingOverview(),
      incidents: { incidents: [pendingIncident()] },
      detail: pendingDetail(),
    });
    render(<App />);

    expect(await screen.findByText(/Verification is pending/)).toBeInTheDocument();
    await openView(user, /^Incidents/);

    await screen.findByRole('heading', { name: 'Incident timeline' });
    expect(screen.getAllByText('Verification pending').length).toBeGreaterThan(0);
    expect(screen.getByText(/No response recorded/)).toBeInTheDocument();
    expect(screen.getByText(/not a confirmation that the person is safe/)).toBeInTheDocument();
    expect(screen.queryByText(/Explicit confirmation recorded/)).not.toBeInTheDocument();
  });

  it('shows backend errors without fabricating data, then recovers on retry', async () => {
    const user = userEvent.setup();
    const mock = installDashboardMock({
      overviewStatus: 503,
      incidentsStatus: 503,
      overviewErrorBody: {
        error: { code: 'SERVICE_UNAVAILABLE', message: 'The backend is restarting.' },
      },
      incidentsErrorBody: {
        error: { code: 'SERVICE_UNAVAILABLE', message: 'The backend is restarting.' },
      },
    });
    render(<App />);

    expect(await screen.findByText('The backend is restarting.')).toBeInTheDocument();
    expect(screen.queryByText('78 bpm')).not.toBeInTheDocument();

    mock.update({
      overview: normalOverview(),
      incidents: { incidents: [] },
      overviewStatus: 200,
      incidentsStatus: 200,
    });
    await user.click(screen.getByRole('button', { name: /Retry/ }));

    expect(await screen.findByText(/Normal operation/)).toBeInTheDocument();
    expect(screen.getAllByText('78 bpm').length).toBeGreaterThan(0);
  });

  it('reports an empty reading state honestly', async () => {
    const overview = normalOverview();
    overview.monitoring = {
      ...overview.monitoring,
      latest_reading: null,
      recent_readings: [],
    };
    installDashboardMock({ overview, incidents: { incidents: [] } });
    render(<App />);

    expect((await screen.findAllByText('No readings available')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0);
    expect(screen.queryByText(/\d+ bpm/)).not.toBeInTheDocument();
  });

  it('displays unknown backend status values verbatim instead of inventing a state', async () => {
    const overview = normalOverview();
    overview.monitoring = {
      ...overview.monitoring,
      status: 'PAUSED',
      detection_status: 'PAUSED',
    };
    installDashboardMock({ overview, incidents: { incidents: [] } });
    render(<App />);

    expect(
      (await screen.findAllByText('PAUSED', { selector: '.stat-card__value' })).length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText('PAUSED').length).toBeGreaterThan(0);
    expect(screen.queryByText(/Normal operation/)).not.toBeInTheDocument();
  });

  it('renders location and seeded nearby hospitals with explicit demo labelling', async () => {
    const user = userEvent.setup();
    installDashboardMock({
      overview: normalOverview(),
      incidents: { incidents: [] },
      location: locationSnapshot(),
      hospitals: hospitalsResponse(),
    });
    render(<App />);

    await screen.findByText(/Normal operation/);
    await openView(user, /^Location & support/);

    expect(await screen.findByText('SAHYOG Demo General Hospital')).toBeInTheDocument();
    expect(screen.getByText('1.2 km')).toBeInTheDocument();
    expect(screen.getByText('3.4 km')).toBeInTheDocument();
    expect(screen.getAllByText('Seeded demo directory').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/No hospital has been contacted/).length).toBeGreaterThan(0);
    expect(screen.getAllByText('18.52040, 73.85670').length).toBeGreaterThan(0);
    expect(screen.getByText('Source: Location service snapshot')).toBeInTheDocument();
  });

  it('shows location and hospital unavailability without crashing', async () => {
    const user = userEvent.setup();
    installDashboardMock({ overview: normalOverview(), incidents: { incidents: [] } });
    render(<App />);

    await screen.findByText(/Normal operation/);
    await openView(user, /^Location & support/);

    expect(await screen.findByText('Location unavailable')).toBeInTheDocument();
    expect(screen.getByText('Hospital lookup unavailable')).toBeInTheDocument();
    expect(screen.queryByText('SAHYOG Demo General Hospital')).not.toBeInTheDocument();
  });

  it('shows a hospital-directory error while keeping the location visible', async () => {
    const user = userEvent.setup();
    installDashboardMock({
      overview: normalOverview(),
      incidents: { incidents: [] },
      location: locationSnapshot(),
      hospitalsStatus: 503,
      hospitalsErrorBody: {
        error: { code: 'HOSPITAL_DIRECTORY_UNAVAILABLE', message: 'Directory offline.' },
      },
    });
    render(<App />);

    await screen.findByText(/Normal operation/);
    await openView(user, /^Location & support/);

    expect(await screen.findByText('Hospital directory unavailable')).toBeInTheDocument();
    expect(screen.getByText('Directory offline.')).toBeInTheDocument();
    expect(screen.getAllByText('18.52040, 73.85670').length).toBeGreaterThan(0);
  });

  it('shows a dedicated authentication-expired state on 401 without fabricating data', async () => {
    installDashboardMock({
      overviewStatus: 401,
      incidentsStatus: 401,
      overviewErrorBody: {
        error: { code: 'UNAUTHORIZED', message: 'Caregiver session expired.' },
      },
      incidentsErrorBody: {
        error: { code: 'UNAUTHORIZED', message: 'Caregiver session expired.' },
      },
    });
    render(<App />);

    expect(await screen.findByText('Dashboard access expired')).toBeInTheDocument();
    expect(screen.getAllByText('Caregiver session expired.').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/No data was fabricated/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/\d+ bpm/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Normal operation/)).not.toBeInTheDocument();
  });

  it('marks an old reading as stale in the monitoring view', async () => {
    const user = userEvent.setup();
    const overview = normalOverview();
    const staleReading = {
      ...overview.monitoring?.latest_reading!,
      reading_id: 'read-stale',
      observed_at: timestamp(-600),
      is_stale: false,
    };
    overview.monitoring = {
      ...overview.monitoring,
      latest_reading: staleReading,
      recent_readings: [staleReading],
      stale_after_seconds: 120,
    };
    installDashboardMock({ overview, incidents: { incidents: [] } });
    render(<App />);

    await screen.findByText(/Normal operation/);
    await openView(user, /^Health monitoring/);

    expect(await screen.findByText(/stale reading/)).toBeInTheDocument();
    expect(screen.getAllByText('Stale').length).toBeGreaterThan(0);
    expect(screen.queryByText('Fresh')).not.toBeInTheDocument();
  });

  it('replaces stale incident data after a repeated demo run refresh', async () => {
    const user = userEvent.setup();
    const mock = installDashboardMock({
      overview: escalatedOverview(),
      incidents: { incidents: [escalatedIncident()] },
      detail: escalatedDetail(),
    });
    render(<App />);

    expect(await screen.findByText(/Escalated incident reported by the backend/)).toBeInTheDocument();

    mock.update({
      overview: normalOverview(),
      incidents: { incidents: [] },
      detail: undefined,
    });
    await user.click(screen.getByRole('button', { name: 'Refresh dashboard data' }));

    expect(await screen.findByText(/Normal operation/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText(/Escalated incident reported by the backend/)).not.toBeInTheDocument();
    });
    expect(screen.queryByLabelText(/active incidents/)).not.toBeInTheDocument();
  });
});
