import { useEditor } from '../../context/EditorContext';

const STAT_ITEMS = [
  { key: 'word_count' as const, label: 'Words', format: (v: number) => v.toLocaleString() },
  { key: 'character_count' as const, label: 'Characters', format: (v: number) => v.toLocaleString() },
  { key: 'character_count_no_spaces' as const, label: 'Chars (no spaces)', format: (v: number) => v.toLocaleString() },
  { key: 'paragraph_count' as const, label: 'Paragraphs', format: (v: number) => v.toLocaleString() },
  { key: 'sentence_count' as const, label: 'Sentences', format: (v: number) => v.toLocaleString() },
  { key: 'heading_count' as const, label: 'Headings', format: (v: number) => v.toLocaleString() },
  { key: 'image_count' as const, label: 'Images', format: (v: number) => v.toLocaleString() },
  { key: 'link_count' as const, label: 'Links', format: (v: number) => v.toLocaleString() },
  { key: 'table_count' as const, label: 'Tables', format: (v: number) => v.toLocaleString() },
  { key: 'code_block_count' as const, label: 'Code Blocks', format: (v: number) => v.toLocaleString() },
  { key: 'reading_time_minutes' as const, label: 'Reading Time', format: (v: number) => `${v} min` },
  { key: 'speaking_time_minutes' as const, label: 'Speaking Time', format: (v: number) => `${v} min` },
  { key: 'flesch_reading_ease' as const, label: 'Readability', format: (v: number) => Math.round(v).toString() },
  { key: 'vocabulary_richness' as const, label: 'Vocab Richness', format: (v: number) => (v * 100).toFixed(1) + '%' },
  { key: 'avg_word_length' as const, label: 'Avg Word Length', format: (v: number) => v.toFixed(1) },
  { key: 'avg_sentence_length' as const, label: 'Avg Sentence', format: (v: number) => v.toFixed(1) },
];

function ReadabilityBar({ score }: { score: number }) {
  const color = score >= 60 ? 'bg-green-500' : score >= 30 ? 'bg-amber-500' : 'bg-red-500';
  const label = score >= 60 ? 'Easy' : score >= 30 ? 'Medium' : 'Hard';
  return (
    <div className="mt-3">
      <div className="flex items-center justify-between text-[10px] text-gray-500 dark:text-gray-400 mb-1">
        <span>Readability: {label}</span>
        <span>{Math.round(score)}/100</span>
      </div>
      <div className="h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all-300 ${color}`} style={{ width: `${Math.min(100, score)}%` }} />
      </div>
    </div>
  );
}

function SEOScoreBar({ score }: { score: number }) {
  const color = score >= 80 ? 'bg-emerald-500' : score >= 60 ? 'bg-amber-500' : 'bg-red-500';
  const label = score >= 80 ? 'Great' : score >= 60 ? 'Good' : 'Needs Work';
  return (
    <div className="mt-2">
      <div className="flex items-center justify-between text-[10px] text-gray-500 dark:text-gray-400 mb-1">
        <span>SEO Score: {label}</span>
        <span>{Math.round(score)}/100</span>
      </div>
      <div className="h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all-300 ${color}`} style={{ width: `${Math.min(100, score)}%` }} />
      </div>
    </div>
  );
}

export default function DocumentStatsPanel() {
  const { state } = useEditor();

  if (!state.statsPanelOpen) return null;

  return (
    <div className="w-56 border-l border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-y-auto flex-shrink-0">
      <div className="p-3 border-b border-gray-100 dark:border-gray-800">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-1.5">
          📊 Statistics
        </h3>
      </div>
      <div className="p-3 space-y-2">
        {state.stats && (
          <>
            <ReadabilityBar score={state.stats.flesch_reading_ease} />
            <SEOScoreBar score={state.seoScore} />
            <div className="border-t border-gray-100 dark:border-gray-800 pt-2 mt-2 grid grid-cols-2 gap-x-3 gap-y-1.5">
              {STAT_ITEMS.map((item) => {
                const value = state.stats![item.key];
                if (value === 0 && !['word_count', 'character_count', 'reading_time_minutes', 'speaking_time_minutes', 'flesch_reading_ease'].includes(item.key)) return null;
                return (
                  <div key={item.key}>
                    <p className="text-[10px] text-gray-400 dark:text-gray-500">{item.label}</p>
                    <p className="text-xs font-semibold text-gray-800 dark:text-gray-200">{item.format(value)}</p>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
