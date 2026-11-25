import { useId } from 'react';
import type { HealthReading } from '../api/types';
import {
  formatClockTime,
  formatDateTime,
  formatSource,
  formatTimestampTitle,
  isReadingStale,
} from '../lib/format';
import { EmptyState } from './EmptyState';

const WIDTH = 760;
const HEIGHT = 260;
const PADDING = { top: 18, right: 18, bottom: 34, left: 46 };

interface ChartProps {
  readings: HealthReading[];
  staleAfterSeconds: number | null | undefined;
}

export function sortReadingsAscending(readings: HealthReading[]): HealthReading[] {
  return [...readings].sort((left, right) => {
    const leftTime = Date.parse(left.observed_at);
    const rightTime = Date.parse(right.observed_at);
    if (!Number.isFinite(leftTime) || !Number.isFinite(rightTime)) {
      return 0;
    }
    return leftTime - rightTime;
  });
}

interface Point {
  x: number;
  y: number;
  reading: HealthReading;
  stale: boolean;
}

function buildPoints(readings: HealthReading[], staleAfterSeconds: number | null | undefined): Point[] {
  if (readings.length === 0) {
    return [];
  }

  const rates = readings.map((reading) => reading.heart_rate_bpm);
  const minRate = Math.min(...rates);
  const maxRate = Math.max(...rates);
  const ratePadding = Math.max(6, Math.round((maxRate - minRate) * 0.2));
  const lower = minRate - ratePadding;
  const upper = maxRate + ratePadding;
  const rateRange = Math.max(1, upper - lower);

  const timestamps = readings.map((reading) => Date.parse(reading.observed_at));
  const hasUsableTimes =
    timestamps.every((timestamp) => Number.isFinite(timestamp)) &&
    new Set(timestamps).size > 1;
  const minTime = hasUsableTimes ? Math.min(...timestamps) : 0;
  const maxTime = hasUsableTimes ? Math.max(...timestamps) : 0;

  const plotWidth = WIDTH - PADDING.left - PADDING.right;
  const plotHeight = HEIGHT - PADDING.top - PADDING.bottom;

  return readings.map((reading, index) => {
    const xRatio = hasUsableTimes
      ? ((timestamps[index] as number) - minTime) / (maxTime - minTime)
      : readings.length === 1
        ? 0.5
        : index / (readings.length - 1);

    return {
      x: PADDING.left + xRatio * plotWidth,
      y: PADDING.top + (1 - (reading.heart_rate_bpm - lower) / rateRange) * plotHeight,
      reading,
      stale: isReadingStale(reading, staleAfterSeconds),
    };
  });
}

function buildLinePath(points: Point[]): string {
  return points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(' ');
}

function buildAreaPath(points: Point[]): string {
  if (points.length === 0) {
    return '';
  }
  const baseline = HEIGHT - PADDING.bottom;
  const first = points[0] as Point;
  const last = points[points.length - 1] as Point;
  return `${buildLinePath(points)} L ${last.x.toFixed(2)} ${baseline} L ${first.x.toFixed(2)} ${baseline} Z`;
}

export function HeartRateChart({ readings, staleAfterSeconds }: ChartProps) {
  const gradientId = useId();
  const usableReadings = sortReadingsAscending(readings)
    .filter((reading) => Number.isFinite(reading.heart_rate_bpm))
    .slice(-30);

  if (usableReadings.length === 0) {
    return (
      <EmptyState
        description="The backend has not returned any heart-rate readings for this monitored person."
        icon="heart"
        title="No readings available"
      />
    );
  }

  const points = buildPoints(usableReadings, staleAfterSeconds);
  const rates = usableReadings.map((reading) => reading.heart_rate_bpm);
  const minRate = Math.min(...rates);
  const maxRate = Math.max(...rates);
  const gridValues = Array.from({ length: 4 }, (_, index) => {
    const ratio = index / 3;
    return Math.round(maxRate + (minRate - maxRate) * ratio);
  });

  const firstReading = usableReadings[0] as HealthReading;
  const lastReading = usableReadings[usableReadings.length - 1] as HealthReading;
  const hasSimulated = usableReadings.some(
    (reading) => reading.source_kind?.toUpperCase() === 'SIMULATED',
  );

  const summary = `${usableReadings.length} readings between ${minRate} and ${maxRate} bpm from ${formatDateTime(
    firstReading.observed_at,
  )} to ${formatDateTime(lastReading.observed_at)}.`;

  return (
    <figure className="chart">
      <svg
        aria-label={summary}
        className="chart__canvas"
        role="img"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#1a8a7c" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#1a8a7c" stopOpacity="0.01" />
          </linearGradient>
        </defs>

        {gridValues.map((value, index) => {
          const y =
            PADDING.top +
            (index / (gridValues.length - 1)) *
              (HEIGHT - PADDING.top - PADDING.bottom);
          return (
            <g key={`${value}-${index}`}>
              <line
                className="chart__grid-line"
                x1={PADDING.left}
                x2={WIDTH - PADDING.right}
                y1={y}
                y2={y}
              />
              <text className="chart__axis-label" x={PADDING.left - 10} y={y + 4} textAnchor="end">
                {value}
              </text>
            </g>
          );
        })}

        <path className="chart__area" d={buildAreaPath(points)} fill={`url(#${gradientId})`} />
        <path className="chart__line" d={buildLinePath(points)} />

        {points.map((point, index) => (
          <circle
            className={`chart__dot${point.stale ? ' chart__dot--stale' : ''}${
              index === points.length - 1 ? ' chart__dot--latest' : ''
            }`}
            cx={point.x}
            cy={point.y}
            key={`${point.reading.reading_id}-${index}`}
            r={index === points.length - 1 ? 5 : 3.2}
          >
            <title>
              {`${formatTimestampTitle(point.reading.observed_at)} | ${
                point.reading.heart_rate_bpm
              } bpm | ${formatSource(point.reading.source_kind)}`}
            </title>
          </circle>
        ))}

        <text
          className="chart__axis-label chart__axis-label--x"
          x={PADDING.left}
          y={HEIGHT - 10}
          textAnchor="start"
        >
          {formatClockTime(firstReading.observed_at)}
        </text>
        <text
          className="chart__axis-label chart__axis-label--x"
          x={WIDTH - PADDING.right}
          y={HEIGHT - 10}
          textAnchor="end"
        >
          {formatClockTime(lastReading.observed_at)}
        </text>
        <text
          className="chart__unit-label"
          x={PADDING.left}
          y={PADDING.top - 4}
          textAnchor="start"
        >
          bpm
        </text>
      </svg>
      <figcaption className="chart__caption">
        <span>{summary}</span>
        <span className="chart__legend">
          <span className="chart__legend-dot" /> Heart rate
          {hasSimulated ? <span className="muted">· Simulated readings</span> : null}
          {points.some((point) => point.stale) ? (
            <span className="muted">· Amber points are stale</span>
          ) : null}
        </span>
      </figcaption>
    </figure>
  );
}

interface SparklineProps {
  readings: HealthReading[];
  staleAfterSeconds: number | null | undefined;
}

export function Sparkline({ readings, staleAfterSeconds }: SparklineProps) {
  const usable = sortReadingsAscending(readings)
    .filter((reading) => Number.isFinite(reading.heart_rate_bpm))
    .slice(-20);

  if (usable.length < 2) {
    return <div className="sparkline sparkline--empty" aria-hidden="true" />;
  }

  const width = 180;
  const height = 48;
  const rates = usable.map((reading) => reading.heart_rate_bpm);
  const min = Math.min(...rates);
  const max = Math.max(...rates);
  const range = Math.max(1, max - min);
  const points = usable.map((reading, index) => {
    const x = (index / (usable.length - 1)) * width;
    const y = height - ((reading.heart_rate_bpm - min) / range) * (height - 8) - 4;
    return { x, y, reading };
  });
  const path = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
    .join(' ');
  const latest = points[points.length - 1];

  return (
    <svg
      aria-hidden="true"
      className="sparkline"
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      width={width}
    >
      <path className="sparkline__line" d={path} />
      {latest ? (
        <circle
          className={`sparkline__dot${
            isReadingStale(latest.reading, staleAfterSeconds) ? ' sparkline__dot--stale' : ''
          }`}
          cx={latest.x}
          cy={latest.y}
          r="3.5"
        />
      ) : null}
    </svg>
  );
}
