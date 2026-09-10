import { motion } from 'framer-motion';
import { CheckCircle2, Loader2, XCircle, Clock, FileText, Languages, Type, AlignLeft } from 'lucide-react';
import type { TranscriptResult, ProcessingResult, ProcessingStep } from '../../types';

interface Props {
  transcript: TranscriptResult;
  isProcessing: boolean;
  processingResult: ProcessingResult | null;
}

const PROCESSING_DISPLAY_STEPS = [
  { key: 'validate_input', label: 'Validating Input', icon: FileText },
  { key: 'normalize_unicode', label: 'Normalizing Unicode', icon: Type },
  { key: 'merge_captions', label: 'Merging Captions', icon: AlignLeft },
  { key: 'fix_punctuation', label: 'Restoring Punctuation', icon: Type },
  { key: 'correct_capitalization', label: 'Fixing Capitalization', icon: Type },
  { key: 'detect_language', label: 'Detecting Language', icon: Languages },
  { key: 'detect_paragraphs', label: 'Formatting Paragraphs', icon: AlignLeft },
  { key: 'calculate_metrics', label: 'Calculating Metrics', icon: Clock },
];

export default function ProcessingPipelineSteps({ transcript, isProcessing, processingResult }: Props) {
  const steps = processingResult?.processing_steps || [];
  const stepMap = new Map(steps.map((s) => [s.name, s]));

  return (
    <div className="rounded-xl border border-violet-100 dark:border-violet-900/50 bg-white dark:bg-gray-900 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-2">
          {isProcessing ? (
            <Loader2 size={16} className="text-violet-500 animate-spin" />
          ) : processingResult?.success ? (
            <CheckCircle2 size={16} className="text-emerald-500" />
          ) : (
            <XCircle size={16} className="text-red-500" />
          )}
          <span className="text-sm font-semibold text-gray-900 dark:text-white">
            AI Processing Pipeline
          </span>
          {isProcessing && (
            <span className="text-xs text-violet-500 dark:text-violet-400 animate-pulse ml-2">
              Processing...
            </span>
          )}
          {processingResult && (
            <span className="text-xs text-gray-400 ml-auto">
              {processingResult.processing_time_ms.toFixed(0)}ms
            </span>
          )}
        </div>
      </div>

      <div className="p-4 space-y-2">
        {PROCESSING_DISPLAY_STEPS.map((stepDef, i) => {
          const actual = stepMap.get(stepDef.key);
          const Icon = stepDef.icon;

          let status: 'pending' | 'running' | 'ok' | 'error' = 'pending';
          if (actual) {
            status = actual.status as any;
          } else if (isProcessing && i === 0) {
            status = 'running';
          } else if (processingResult?.success) {
            status = 'ok';
          }

          return (
            <motion.div
              key={stepDef.key}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                status === 'ok'
                  ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300'
                  : status === 'running'
                  ? 'bg-violet-50 dark:bg-violet-900/20 text-violet-700 dark:text-violet-300'
                  : status === 'error'
                  ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                  : 'text-gray-400 dark:text-gray-500'
              }`}
            >
              {status === 'ok' ? (
                <CheckCircle2 size={16} className="shrink-0 text-emerald-500" />
              ) : status === 'running' ? (
                <Loader2 size={16} className="shrink-0 text-violet-500 animate-spin" />
              ) : status === 'error' ? (
                <XCircle size={16} className="shrink-0 text-red-500" />
              ) : (
                <div className="w-4 h-4 rounded-full border-2 border-gray-300 dark:border-gray-600 shrink-0" />
              )}
              <Icon size={14} className="shrink-0 opacity-60" />
              <span className="font-medium">{stepDef.label}</span>
              {actual?.detail && status === 'ok' && (
                <span className="text-xs opacity-60 ml-auto truncate max-w-[200px]">
                  {actual.detail}
                </span>
              )}
              {actual?.duration_ms != null && (
                <span className="text-[10px] opacity-40 ml-1 shrink-0">
                  {actual.duration_ms.toFixed(0)}ms
                </span>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Stats summary */}
      {processingResult?.success && (
        <div className="px-4 py-3 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
          <div className="flex flex-wrap gap-4 text-xs text-gray-500 dark:text-gray-400">
            <span>
              <strong className="text-gray-700 dark:text-gray-300">
                {processingResult.statistics.word_count.toLocaleString()}
              </strong>{' '}
              words
            </span>
            <span>
              <strong className="text-gray-700 dark:text-gray-300">
                {processingResult.statistics.sentence_count}
              </strong>{' '}
              sentences
            </span>
            <span>
              <strong className="text-gray-700 dark:text-gray-300">
                {processingResult.statistics.paragraph_count}
              </strong>{' '}
              paragraphs
            </span>
            <span>
              ⏱{' '}
              <strong className="text-gray-700 dark:text-gray-300">
                {processingResult.statistics.estimated_read_time}
              </strong>
            </span>
            <span>
              🌐{' '}
              <strong className="text-gray-700 dark:text-gray-300">
                {processingResult.language?.primary?.toUpperCase() || 'EN'}
              </strong>
              {processingResult.language?.secondary && (
                <> + {processingResult.language.secondary.toUpperCase()}</>
              )}
            </span>
            {processingResult.statistics.filler_word_count > 0 && (
              <span>
                🗑️{' '}
                <strong className="text-gray-700 dark:text-gray-300">
                  {processingResult.statistics.filler_word_count}
                </strong>{' '}
                fillers
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
