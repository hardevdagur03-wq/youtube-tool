export default function WorkflowSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-6 w-48 bg-gray-200 dark:bg-gray-700 rounded-lg" />
      <div className="h-4 w-72 bg-gray-200 dark:bg-gray-700 rounded-lg" />
      <div className="h-64 rounded-2xl bg-gray-100 dark:bg-gray-800" />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-20 rounded-xl bg-gray-100 dark:bg-gray-800" />
        ))}
      </div>
      <div className="h-32 rounded-2xl bg-gray-100 dark:bg-gray-800" />
    </div>
  );
}
