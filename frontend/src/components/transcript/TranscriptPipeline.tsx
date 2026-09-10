import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircle2,
  XCircle,
  Loader2,
  SkipForward,
  Clock,
  Circle,
} from 'lucide-react';
import type { PipelineStep, PipelineStepStatus } from '../../types';

const statusConfig: Record<
  PipelineStepStatus,
  { icon: typeof CheckCircle2; color: string; bg: string }
> = {
  pending: {
    icon: Clock,
    color: 'text-gray-400 dark:text-gray-500',
    bg: 'bg-gray-100 dark:bg-gray-800',
  },
  running: {
    icon: Loader2,
    color: 'text-violet-500',
    bg: 'bg-violet-50 dark:bg-violet-900/20',
  },
  ok: {
    icon: CheckCircle2,
    color: 'text-emerald-500',
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
  },
  error: {
    icon: XCircle,
    color: 'text-red-500',
    bg: 'bg-red-50 dark:bg-red-900/20',
  },
  skipped: {
    icon: SkipForward,
    color: 'text-amber-500',
    bg: 'bg-amber-50 dark:bg-amber-900/20',
  },
};

interface TranscriptPipelineProps {
  steps: PipelineStep[];
}

function isManualNotAvailable(step: PipelineStep): boolean {
  const name = step.name?.toLowerCase() || '';
  return (
    name.includes('manual') &&
    (step.status === 'skipped' || step.status === 'error')
  );
}

function getStepDisplay(step: PipelineStep): {
  icon: typeof CheckCircle2;
  color: string;
  bg: string;
  detail: string;
} {
  const config = statusConfig[step.status] || statusConfig.pending;
  const Icon = config.icon;

  // If manual transcript is skipped/error, show it as "Not Available"
  if (isManualNotAvailable(step)) {
    return {
      icon: Circle,
      color: 'text-gray-400 dark:text-gray-500',
      bg: 'bg-gray-50 dark:bg-gray-800/50',
      detail: 'Not Available',
    };
  }

  return {
    icon: Icon,
    color: config.color,
    bg: config.bg,
    detail: step.detail || '',
  };
}

export default function TranscriptPipeline({ steps }: TranscriptPipelineProps) {
  if (steps.length === 0) return null;

  const completed = steps.filter(
    (s) => s.status === 'ok' || s.status === 'error' || s.status === 'skipped',
  ).length;
  const progress = Math.round((completed / steps.length) * 100);

  return (
    <div className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-6">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          Pipeline Progress
        </h3>
        <span className="text-xs font-medium text-gray-400 dark:text-gray-500">
          {completed}/{steps.length} steps
        </span>
      </div>

      <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-1.5 mb-5 overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-violet-500 to-emerald-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>

      <div className="space-y-2">
        <AnimatePresence>
          {steps.map((step, i) => {
            const display = getStepDisplay(step);
            const Icon = display.icon;

            return (
              <motion.div
                key={`${step.name}-${i}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08, duration: 0.3 }}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm ${display.bg}`}
              >
                <div className="flex-shrink-0">
                  {step.status === 'running' ? (
                    <Loader2 size={15} className={`animate-spin ${display.color}`} />
                  ) : (
                    <Icon size={15} className={display.color} />
                  )}
                </div>
                <span className="flex-1 font-medium text-gray-700 dark:text-gray-300">
                  {step.name}
                </span>
                <span className="text-xs text-gray-400 dark:text-gray-500 truncate max-w-[200px]">
                  {display.detail}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
