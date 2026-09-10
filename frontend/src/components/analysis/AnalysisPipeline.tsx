import { motion } from 'framer-motion';
import { Sparkles, Search, Tag, Users, ListOrdered, Brain, CheckCircle2, Loader2, XCircle } from 'lucide-react';

const ANALYSIS_STEPS = [
  { key: 'understanding', label: 'Understanding Content', icon: Brain },
  { key: 'topics', label: 'Detecting Topics', icon: Search },
  { key: 'keywords', label: 'Extracting Keywords', icon: Tag },
  { key: 'entities', label: 'Identifying Entities', icon: Users },
  { key: 'outline', label: 'Building Outline', icon: ListOrdered },
  { key: 'context', label: 'Generating AI Context', icon: Sparkles },
];

interface Props {
  status: 'idle' | 'analyzing' | 'ok' | 'error';
  processingTimeMs?: number;
  provider?: string;
  model?: string;
}

export default function AnalysisPipeline({ status, processingTimeMs, provider, model }: Props) {
  const isProcessing = status === 'analyzing';
  const isComplete = status === 'ok';

  return (
    <div className="rounded-xl border border-indigo-100 dark:border-indigo-900/50 bg-white dark:bg-gray-900 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-2">
          {isProcessing ? (
            <Loader2 size={16} className="text-indigo-500 animate-spin" />
          ) : isComplete ? (
            <CheckCircle2 size={16} className="text-emerald-500" />
          ) : status === 'error' ? (
            <XCircle size={16} className="text-red-500" />
          ) : (
            <Sparkles size={16} className="text-indigo-400" />
          )}
          <span className="text-sm font-semibold text-gray-900 dark:text-white">
            AI Content Analysis
          </span>
          {isProcessing && (
            <span className="text-xs text-indigo-500 dark:text-indigo-400 animate-pulse ml-2">
              Analyzing...
            </span>
          )}
          {isComplete && processingTimeMs != null && (
            <span className="text-xs text-gray-400 ml-auto">
              {processingTimeMs.toFixed(0)}ms
              {model && ` · ${model}`}
            </span>
          )}
        </div>
      </div>

      <div className="p-4 space-y-2">
        {ANALYSIS_STEPS.map((stepDef, i) => {
          const Icon = stepDef.icon;

          let stepStatus: 'pending' | 'running' | 'ok' | 'error' = 'pending';
          if (isComplete) {
            stepStatus = 'ok';
          } else if (isProcessing && i === 0) {
            stepStatus = 'running';
          } else if (status === 'error' && i === 0) {
            stepStatus = 'error';
          }

          return (
            <motion.div
              key={stepDef.key}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                stepStatus === 'ok'
                  ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300'
                  : stepStatus === 'running'
                  ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300'
                  : stepStatus === 'error'
                  ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                  : 'text-gray-400 dark:text-gray-500'
              }`}
            >
              {stepStatus === 'ok' ? (
                <CheckCircle2 size={16} className="shrink-0 text-emerald-500" />
              ) : stepStatus === 'running' ? (
                <Loader2 size={16} className="shrink-0 text-indigo-500 animate-spin" />
              ) : stepStatus === 'error' ? (
                <XCircle size={16} className="shrink-0 text-red-500" />
              ) : (
                <div className="w-4 h-4 rounded-full border-2 border-gray-300 dark:border-gray-600 shrink-0" />
              )}
              <Icon size={14} className="shrink-0 opacity-60" />
              <span className="font-medium">{stepDef.label}</span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
