import { clsx } from "clsx";

export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        "animate-pulse rounded-md bg-surface-elevated border border-stroke/50",
        className
      )}
      {...props}
    />
  );
}
