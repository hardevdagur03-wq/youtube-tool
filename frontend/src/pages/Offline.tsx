import { useState } from 'react';

export default function Offline() {
  const [checking, setChecking] = useState(false);
  const [online, setOnline] = useState(false);

  const handleCheck = async () => {
    setChecking(true);
    try {
      await fetch('/api/health', { signal: AbortSignal.timeout(5000) });
      setOnline(true);
      window.location.reload();
    } catch {
      setOnline(false);
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center p-8 max-w-md">
        <div className="w-20 h-20 rounded-full bg-yellow-50 dark:bg-yellow-900/30 flex items-center justify-center mx-auto mb-6">
          <span className="text-4xl font-bold text-yellow-500">!</span>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          No connection
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mb-6">
          You appear to be offline. Check your internet connection and try again.
        </p>
        <button
          onClick={handleCheck}
          disabled={checking}
          className="inline-flex items-center px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {checking ? 'Checking...' : 'Try again'}
        </button>
        {online && (
          <p className="mt-3 text-sm text-green-600 dark:text-green-400">
            Connected! Reloading...
          </p>
        )}
      </div>
    </div>
  );
}
