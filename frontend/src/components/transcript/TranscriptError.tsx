import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Card } from '../ui';

interface TranscriptErrorProps {
  message: string;
  onRetry?: () => void;
}

export default function TranscriptError({ message, onRetry }: TranscriptErrorProps) {
  const isNetworkError = message.toLowerCase().includes('network') || message.toLowerCase().includes('fetch');
  const isUnavailable = message.toLowerCase().includes('no transcript') || message.toLowerCase().includes('unavailable');
  const isQuota = message.toLowerCase().includes('quota') || message.toLowerCase().includes('rate limit');

  const variant = isQuota ? 'Quota Exceeded' : isNetworkError ? 'Network Error' : isUnavailable ? 'Transcript Unavailable' : 'Error';

  return (
    <Card padding="lg" className="mb-6 border-red-200 dark:border-red-800/50">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-red-50 dark:bg-red-900/30 flex items-center justify-center flex-shrink-0">
          <AlertTriangle size={18} className="text-red-600 dark:text-red-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
            {variant}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            {message}
          </p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/50 transition-all-200"
            >
              <RefreshCw size={14} />
              Retry
            </button>
          )}
        </div>
      </div>
    </Card>
  );
}
