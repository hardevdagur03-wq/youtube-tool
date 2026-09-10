import { Languages, Loader2 } from 'lucide-react';
import type { TranscriptTab } from '../../types';

interface LanguageSelectorProps {
  tabs: TranscriptTab[];
  activeTab: string;
  onSelect: (key: string) => void;
  disabled?: boolean;
}

export default function LanguageSelector({
  tabs,
  activeTab,
  onSelect,
  disabled = false,
}: LanguageSelectorProps) {
  if (tabs.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <Languages size={14} className="text-gray-400 mr-1" />
      {tabs.map((tab) => {
        const isActive = tab.key === activeTab;
        const isDisabled = !tab.available || disabled;

        return (
          <button
            key={tab.key}
            onClick={() => {
              if (!isDisabled && !isActive) {
                onSelect(tab.key);
              }
            }}
            disabled={isDisabled}
            title={
              !tab.available
                ? `${tab.label} — Not Available`
                : tab.label
            }
            className={`relative px-3 py-1.5 rounded-lg text-xs font-medium transition-all-200 ${
              isActive
                ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                : isDisabled
                ? 'bg-gray-50 dark:bg-gray-800/30 text-gray-400 dark:text-gray-600 border border-gray-100 dark:border-gray-800 cursor-not-allowed line-through decoration-gray-300 dark:decoration-gray-600'
                : 'bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer'
            }`}
          >
            {!tab.available && (
              <span className="absolute -top-1 -right-1 w-2 h-2 bg-gray-300 dark:bg-gray-600 rounded-full" />
            )}
            {tab.label}
            {isActive && disabled && (
              <Loader2 size={10} className="inline ml-1 animate-spin" />
            )}
          </button>
        );
      })}
    </div>
  );
}
