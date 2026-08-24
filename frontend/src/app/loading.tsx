export default function DashboardLoading() {
  return (
    <div className="space-y-10" aria-busy="true" aria-label="Loading shop data">
      <div>
        <div className="mb-2 h-3 w-32 animate-pulse rounded-sm bg-kraft/50" />
        <div className="doc-panel grid h-[76px] grid-cols-2 md:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="border-r border-rule px-4 py-3 last:border-r-0">
              <div className="h-2 w-16 animate-pulse rounded-sm bg-kraft/40" />
              <div className="mt-2 h-5 w-20 animate-pulse rounded-sm bg-kraft/60" />
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-2 h-3 w-24 animate-pulse rounded-sm bg-kraft/50" />
        <div className="doc-panel h-56 p-4">
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="h-3 w-48 animate-pulse rounded-sm bg-kraft/40" />
                <div className="h-3 w-10 animate-pulse rounded-sm bg-kraft/60" />
              </div>
            ))}
          </div>
        </div>
      </div>

      <span className="sr-only">Loading shop data…</span>
    </div>
  );
}
