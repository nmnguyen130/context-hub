export default function AuthLoading() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-5 w-48 bg-surface-elevated rounded mx-auto"></div>
      <div className="h-3 w-64 bg-surface-elevated rounded mx-auto"></div>
      <div className="space-y-3 pt-4">
        <div className="h-10 bg-surface-elevated rounded-md"></div>
        <div className="h-10 bg-surface-elevated rounded-md"></div>
        <div className="h-10 bg-surface-elevated rounded-md"></div>
      </div>
    </div>
  );
}
