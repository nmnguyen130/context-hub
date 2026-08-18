export default function DashboardLoading() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-pulse">
      {/* Top Header Skeleton */}
      <div className="flex items-center justify-between pb-4 border-b border-stroke">
        <div className="space-y-2">
          <div className="h-3 w-40 bg-surface-elevated rounded"></div>
          <div className="h-6 w-56 bg-surface-elevated rounded"></div>
        </div>
        <div className="flex gap-2">
          <div className="h-8 w-28 bg-surface-elevated rounded"></div>
          <div className="h-8 w-32 bg-surface-elevated rounded"></div>
        </div>
      </div>

      {/* 4 Cards Skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="h-24 rounded-lg bg-surface border border-stroke"></div>
        <div className="h-24 rounded-lg bg-surface border border-stroke"></div>
        <div className="h-24 rounded-lg bg-surface border border-stroke"></div>
        <div className="h-24 rounded-lg bg-surface border border-stroke"></div>
      </div>

      {/* Main Content Grid Skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 h-64 rounded-lg bg-surface border border-stroke"></div>
        <div className="lg:col-span-5 h-64 rounded-lg bg-surface border border-stroke"></div>
      </div>
    </div>
  );
}
