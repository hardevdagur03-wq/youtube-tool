import { ArrowLeft, ArrowRight, RotateCcw } from 'lucide-react';
import type { WorkflowStep } from '../../types';

const stepOrder: WorkflowStep[] = ['url', 'metadata', 'transcript', 'analysis', 'generate', 'editor', 'export'];

interface WorkflowFooterProps {
  currentStep: WorkflowStep;
  onBack?: () => void;
  onContinue?: () => void;
  disableBack?: boolean;
  disableContinue?: boolean;
  continueLabel?: string;
  showReset?: boolean;
  onReset?: () => void;
}

export default function WorkflowFooter({
  currentStep,
  onBack,
  onContinue,
  disableBack = false,
  disableContinue = false,
  continueLabel = 'Continue',
  showReset = false,
  onReset,
}: WorkflowFooterProps) {
  const currentIndex = stepOrder.indexOf(currentStep);
  const isLast = currentIndex === stepOrder.length - 1;

  return (
    <div className="flex items-center justify-between pt-6 mt-8 border-t border-gray-100 dark:border-gray-800">
      <div className="flex items-center gap-3">
        {onBack && (
          <button
            onClick={onBack}
            disabled={disableBack}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-all-200"
          >
            <ArrowLeft size={14} />
            Back
          </button>
        )}
        {showReset && onReset && (
          <button
            onClick={onReset}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium text-gray-400 dark:text-gray-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all-200"
          >
            <RotateCcw size={12} />
            Reset
          </button>
        )}
      </div>

      {onContinue && (
        <button
          onClick={onContinue}
          disabled={disableContinue}
          className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold bg-violet-600 text-white hover:bg-violet-500 active:bg-violet-700 disabled:bg-gray-200 dark:disabled:bg-gray-800 disabled:text-gray-400 dark:disabled:text-gray-600 disabled:cursor-not-allowed shadow-lg shadow-violet-200 dark:shadow-violet-900/30 hover:shadow-xl transition-all-200"
        >
          {isLast ? 'Finish' : continueLabel}
          <ArrowRight size={14} />
        </button>
      )}

      {!onContinue && !onBack && (
        <div className="text-xs text-gray-400 dark:text-gray-500">
          Step {currentIndex + 1} of {stepOrder.length}
        </div>
      )}
    </div>
  );
}
