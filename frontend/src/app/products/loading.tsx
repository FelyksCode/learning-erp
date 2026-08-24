export default function ProductsLoading() {
  return (
    <div className="space-y-8" aria-busy="true" aria-label="Loading products">
      <div className="flex items-center justify-between">
        <div className="h-5 w-40 animate-pulse rounded-sm bg-kraft/50" />
        <div className="h-8 w-44 animate-pulse rounded-sm bg-kraft/40" />
      </div>
      <div className="doc-panel h-36 p-5">
        <div className="h-2.5 w-40 animate-pulse rounded-sm bg-kraft/50" />
        <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-7 animate-pulse rounded-sm bg-kraft/30" />
          ))}
        </div>
      </div>
      <div className="doc-panel h-64 p-4">
        <div className="space-y-3">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="flex items-center justify-between">
              <div className="h-3 w-56 animate-pulse rounded-sm bg-kraft/40" />
              <div className="h-3 w-24 animate-pulse rounded-sm bg-kraft/60" />
            </div>
          ))}
        </div>
      </div>
      <span className="sr-only">Loading products…</span>
    </div>
  );
}
