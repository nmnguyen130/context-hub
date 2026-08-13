import { clsx } from "clsx";

export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        "animate-pulse rounded-md bg-slate-800/80 border border-slate-700/40",
        className
      )}
      {...props}
    />
  );
}
