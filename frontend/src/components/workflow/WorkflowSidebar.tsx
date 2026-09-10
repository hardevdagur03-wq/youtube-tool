import { motion } from 'framer-motion';
import { CheckCircle2, Circle, Loader2, XCircle, SkipForward } from 'lucide-react';
import type { WorkflowStep } from '../../types';

const stepNames: Record<WorkflowStep, string> = {
  url: 'Video URL',
  metadata: 'Metadata Retrieved',
  transcript: 'Transcript Extraction',
  analysis: 'AI Analysis',
  generate: 'Blog Generation',
  editor: 'Editor Review',
  export: 'Export',
};

interface WorkflowSidebarProps {
  currentStep: WorkflowStep;
  stepStatus: Record<WorkflowStep, 'pending' | 'running' | 'ok' | 'error' | 'skipped'>;
}

export default function WorkflowSidebar({ currentStep, stepStatus }: WorkflowSidebarProps) {
  const steps = Object.keys(stepNames) as WorkflowStep[];

  return (
    <div className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 sticky top-[140px]">
      <h3 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-4">
        Workflow Progress
      </h3>
      <div className="space-y-1">
        {steps.map((step, i) => {
          const status = stepStatus[step];
          const isActive = step === currentStep;
          const isCompleted = status === 'ok';
          const isError = status === 'error';
          const isSkipped = status === 'skipped';

          let Icon = Circle;
          let color = 'text-gray-300 dark:text-gray-600';
          let bg = 'bg-transparent';
          let lineColor = 'bg-gray-100 dark:bg-gray-800';

          if (isCompleted) {
            Icon = CheckCircle2;
            color = 'text-emerald-500';
            bg = 'bg-emerald-50 dark:bg-emerald-900/20';
            lineColor = 'bg-emerald-200 dark:bg-emerald-800';
          } else if (isActive) {
            Icon = Loader2;
            color = 'text-violet-500';
            bg = 'bg-violet-50 dark:bg-violet-900/20';
            lineColor = 'bg-violet-200 dark:bg-violet-800';
          } else if (isError) {
            Icon = XCircle;
            color = 'text-red-500';
            bg = 'bg-red-50 dark:bg-red-900/20';
          } else if (isSkipped) {
            Icon = SkipForward;
            color = 'text-amber-500';
            lineColor = 'bg-amber-200 dark:bg-amber-800';
          } else {
            Icon = Circle;
            color = 'text-gray-300 dark:text-gray-600';
          }

          return (
            <div key={step} className="flex gap-3">
              <div className="flex flex-col items-center gap-1">
                <motion.div
                  initial={false}
                  animate={{ scale: isActive ? 1.1 : 1 }}
                  className={`p-1 rounded-lg ${bg}`}
                >
                  {isActive ? (
                    <Loader2 size={14} className={`animate-spin ${color}`} />
                  ) : (
                    <Icon size={14} className={color} />
                  )}
                </motion.div>
                {i < steps.length - 1 && (
                  <div className={`w-[2px] h-6 ${lineColor} rounded-full`} />
                )}
              </div>
              <div className="pb-3">
                <span
                  className={`text-sm font-medium transition-colors-200 ${
                    isCompleted
                      ? 'text-emerald-700 dark:text-emerald-300'
                      : isActive
                        ? 'text-violet-700 dark:text-violet-300'
                        : isError
                          ? 'text-red-600 dark:text-red-400'
                          : 'text-gray-400 dark:text-gray-500'
                  }`}
                >
                  {stepNames[step]}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
