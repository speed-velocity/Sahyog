import type { ReactNode } from 'react';

export type IconName =
  | 'activity'
  | 'alert'
  | 'check'
  | 'chevronRight'
  | 'clock'
  | 'heart'
  | 'hospital'
  | 'incident'
  | 'location'
  | 'overview'
  | 'phone'
  | 'refresh'
  | 'shield'
  | 'user';

const ICONS: Record<IconName, ReactNode> = {
  overview: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </>
  ),
  heart: (
    <path d="M20.8 5.6a5.5 5.5 0 0 0-7.8 0L12 6.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 22l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z" />
  ),
  incident: (
    <>
      <path d="M12 3 2.5 20h19L12 3Z" />
      <path d="M12 9v4" />
      <path d="M12 17h.01" />
    </>
  ),
  location: (
    <>
      <path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z" />
      <circle cx="12" cy="10" r="2.5" />
    </>
  ),
  refresh: (
    <>
      <path d="M20 7v5h-5" />
      <path d="M4 17v-5h5" />
      <path d="M6.1 9a7 7 0 0 1 11.5-2.6L20 9" />
      <path d="M17.9 15a7 7 0 0 1-11.5 2.6L4 15" />
    </>
  ),
  chevronRight: <path d="m9 18 6-6-6-6" />,
  alert: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v6" />
      <path d="M12 17h.01" />
    </>
  ),
  check: (
    <>
      <path d="m5 12.5 4.5 4.5L19 7" />
    </>
  ),
  phone: (
    <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.9a2 2 0 0 1-.4 2.1L8.1 10a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.9.6 2.9.7a2 2 0 0 1 1.6 1.9Z" />
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  shield: (
    <>
      <path d="M12 22s8-3.5 8-10V5l-8-3-8 3v7c0 6.5 8 10 8 10Z" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  hospital: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M9 3h6v4H9z" />
      <path d="M12 11v6" />
      <path d="M9 14h6" />
    </>
  ),
  activity: <path d="M3 12h4l2.5-7 4 14 2.5-7h5" />,
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </>
  ),
};

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
}

export function Icon({ name, size = 18, className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      height={size}
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
      width={size}
    >
      {ICONS[name]}
    </svg>
  );
}
