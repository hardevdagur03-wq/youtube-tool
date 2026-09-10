export default function TranscriptSkeleton() {
  return (
    <div className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 mb-6 animate-pulse">
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gray-200 dark:bg-gray-700" />
          <div>
            <div className="h-4 w-28 bg-gray-200 dark:bg-gray-700 rounded-md mb-2" />
            <div className="flex gap-2">
              <div className="h-5 w-16 bg-gray-200 dark:bg-gray-700 rounded-full" />
              <div className="h-5 w-12 bg-gray-200 dark:bg-gray-700 rounded-full" />
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <div className="h-8 w-16 bg-gray-200 dark:bg-gray-700 rounded-xl" />
          <div className="h-8 w-20 bg-gray-200 dark:bg-gray-700 rounded-xl" />
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="px-4 py-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800">
            <div className="h-3 w-14 bg-gray-200 dark:bg-gray-700 rounded mb-2" />
            <div className="h-4 w-20 bg-gray-200 dark:bg-gray-700 rounded" />
          </div>
        ))}
      </div>

      <div className="space-y-3">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="flex gap-3 px-5 py-3">
            <div className="h-3 w-14 bg-gray-200 dark:bg-gray-700 rounded flex-shrink-0" />
            <div className="h-3 flex-1 bg-gray-200 dark:bg-gray-700 rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}
