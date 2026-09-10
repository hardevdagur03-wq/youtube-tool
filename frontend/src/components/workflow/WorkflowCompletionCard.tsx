import { motion } from 'framer-motion';
import { CheckCircle2, ArrowRight, Clock, Loader2, XCircle } from 'lucide-react';
import { Card, Badge } from '../ui';

interface WorkflowCompletionCardProps {
  title: string;
  subtitle: string;
  nextStepLabel: string;
  nextStepDescription: string;
  estimatedTime: string;
  status: 'ok' | 'running' | 'error';
  error?: string | null;
  onContinue: () => void;
  loading?: boolean;
}

export default function WorkflowCompletionCard({
  title,
  subtitle,
  nextStepLabel,
  nextStepDescription,
  estimatedTime,
  status,
  error,
  onContinue,
  loading = false,
}: WorkflowCompletionCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <Card padding="lg" className={`border-2 ${
        status === 'ok'
          ? 'border-emerald-200 dark:border-emerald-800'
          : status === 'error'
            ? 'border-red-200 dark:border-red-800'
            : 'border-violet-200 dark:border-violet-800'
      }`}>
        <div className="flex items-start gap-4">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 300, damping: 15, delay: 0.2 }}
            className={`w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 ${
              status === 'ok'
                ? 'bg-emerald-50 dark:bg-emerald-900/30'
                : status === 'error'
                  ? 'bg-red-50 dark:bg-red-900/30'
                  : 'bg-violet-50 dark:bg-violet-900/30'
            }`}
          >
            {status === 'ok' ? (
              <CheckCircle2 size={24} className="text-emerald-500" />
            ) : status === 'error' ? (
              <XCircle size={24} className="text-red-500" />
            ) : (
              <Loader2 size={24} className="animate-spin text-violet-500" />
            )}
          </motion.div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              {status === 'ok' && <Badge variant="success">Completed</Badge>}
              {status === 'running' && <Badge variant="info">In Progress</Badge>}
              {status === 'error' && <Badge variant="error">Failed</Badge>}
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
              {title}
            </h3>
            {error ? (
              <p className="text-sm text-red-500 dark:text-red-400 mb-4">{error}</p>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{subtitle}</p>
            )}

            {status === 'ok' && (
              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                <button
                  onClick={onContinue}
                  disabled={loading}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm bg-violet-600 text-white hover:bg-violet-500 active:bg-violet-700 shadow-lg shadow-violet-200 dark:shadow-violet-900/30 hover:shadow-xl transition-all-200"
                >
                  {loading ? (
                    <Loader2 size={15} className="animate-spin" />
                  ) : (
                    <ArrowRight size={15} />
                  )}
                  {nextStepLabel}
                </button>
                <div className="flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500">
                  <Clock size={12} />
                  {estimatedTime}
                </div>
              </div>
            )}

            {status === 'ok' && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="mt-3 text-sm text-gray-400 dark:text-gray-500"
              >
                {nextStepDescription}
              </motion.p>
            )}
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
