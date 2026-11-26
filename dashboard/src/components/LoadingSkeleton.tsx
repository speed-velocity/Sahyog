interface LoadingSkeletonProps {
  rows?: number;
  cards?: number;
  label?: string;
}

export function LoadingSkeleton({ rows = 3, cards = 0, label = 'Loading data' }: LoadingSkeletonProps) {
  return (
    <div aria-busy="true" aria-label={label} className="loading-skeleton" role="status">
      {cards > 0 ? (
        <div className="loading-skeleton__cards">
          {Array.from({ length: cards }, (_, index) => (
            <div className="skeleton skeleton--card" key={index} />
          ))}
        </div>
      ) : null}
      <div className="loading-skeleton__rows">
        {Array.from({ length: rows }, (_, index) => (
          <div className="skeleton skeleton--row" key={index} />
        ))}
      </div>
    </div>
  );
}
