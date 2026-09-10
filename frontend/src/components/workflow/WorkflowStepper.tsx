import { motion } from 'framer-motion';
import { Check, ArrowRight, Youtube, Search, FileText, Brain, PenLine, FileEdit, Download } from 'lucide-react';
import type { WorkflowStep } from '../../types';

const stepIcons: Record<WorkflowStep, typeof Youtube> = {
  url: Youtube,
  metadata: Search,
  transcript: FileText,
  analysis: Brain,
  generate: PenLine,
  editor: FileEdit,
  export: Download,
};

const stepLabels: Record<WorkflowStep, string> = {
  url: 'URL',
  metadata: 'Metadata',
  transcript: 'Transcript',
  analysis: 'Analysis',
  generate: 'Generate',
  editor: 'Editor',
  export: 'Export',
};

interface WorkflowStepperProps {
  currentStep: WorkflowStep;
  stepStatus: Record<WorkflowStep, 'pending' | 'running' | 'ok' | 'error' | 'skipped'>;
}

export default function WorkflowStepper({ currentStep, stepStatus }: WorkflowStepperProps) {
  const steps = Object.keys(stepLabels) as WorkflowStep[];
  const currentIndex = steps.indexOf(currentStep);

  return (
    <div className="sticky top-16 lg:top-[68px] z-40 bg-white/95 dark:bg-gray-950/95 backdrop-blur-xl border-b border-gray-100 dark:border-gray-800 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div className="flex items-center justify-between">
          {steps.map((step, i) => {
            const icon = stepIcons[step];
            const Icon = icon;
            const status = stepStatus[step];
            const isActive = step === currentStep;
            const isCompleted = status === 'ok';
            const isError = status === 'error';
            const isFuture = i > currentIndex;

            return (
              <div key={step} className="flex items-center flex-1 last:flex-none">
                <div className="flex items-center gap-2">
                  <motion.div
                    initial={false}
                    animate={{
                      scale: isActive ? 1 : 0.95,
                    }}
                    className={`relative w-8 h-8 rounded-xl flex items-center justify-center transition-all-200 ${
                      isCompleted
                        ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-200 dark:shadow-emerald-900/30'
                        : isActive
                          ? 'bg-violet-600 text-white shadow-lg shadow-violet-200 dark:shadow-violet-900/30 ring-2 ring-violet-200 dark:ring-violet-800'
                          : isError
                            ? 'bg-red-500 text-white'
                            : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500'
                    }`}
                  >
                    {isCompleted ? (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: 'spring', stiffness: 400, damping: 20 }}
                      >
                        <Check size={14} strokeWidth={3} />
                      </motion.div>
                    ) : (
                      <Icon size={14} />
                    )}
                  </motion.div>
                  <span
                    className={`hidden sm:block text-xs font-semibold transition-colors-200 ${
                      isCompleted
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : isActive
                          ? 'text-gray-900 dark:text-white'
                          : isFuture
                            ? 'text-gray-300 dark:text-gray-600'
                            : 'text-gray-500 dark:text-gray-400'
                    }`}
                  >
                    {stepLabels[step]}
                  </span>
                </div>
                {i < steps.length - 1 && (
                  <div className="flex-1 mx-2 sm:mx-3">
                    <div className="h-[2px] bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: '0%' }}
                        animate={{
                          width: isCompleted ? '100%' : isActive && status === 'running' ? '50%' : '0%',
                        }}
                        transition={{ duration: 0.5, ease: 'easeOut' }}
                        className={`h-full rounded-full ${
                          isCompleted
                            ? 'bg-emerald-500'
                            : isActive
                              ? 'bg-violet-500'
                              : 'bg-transparent'
                        }`}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
