import { useState, useCallback, useEffect, useRef } from 'react';
import { useEditor } from '../../context/EditorContext';
import type { FindReplaceRequest, FindReplaceResult } from '../../types/editor';

export default function FindReplacePanel() {
  const { state, findText, replaceText } = useEditor();
  const [query, setQuery] = useState('');
  const [replacement, setReplacement] = useState('');
  const [useRegex, setUseRegex] = useState(false);
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [wholeWord, setWholeWord] = useState(false);
  const [result, setResult] = useState<FindReplaceResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (state.findReplaceOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [state.findReplaceOpen]);

  const handleFind = useCallback(async () => {
    if (!query) return;
    const req: FindReplaceRequest = {
      query, replacement, use_regex: useRegex,
      case_sensitive: caseSensitive, whole_word: wholeWord,
      scope: 'document',
    };
    const res = await findText(req);
    setResult(res);
  }, [query, replacement, useRegex, caseSensitive, wholeWord, findText]);

  const handleReplace = useCallback(async () => {
    if (!query) return;
    const req: FindReplaceRequest = {
      query, replacement, use_regex: useRegex,
      case_sensitive: caseSensitive, whole_word: wholeWord,
      scope: 'document',
    };
    const res = await replaceText(req);
    setResult(res);
  }, [query, replacement, useRegex, caseSensitive, wholeWord, replaceText]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleFind();
    }
  }, [handleFind]);

  if (!state.findReplaceOpen) return null;

  return (
    <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-4 py-3">
      <div className="flex items-center gap-3 max-w-2xl">
        <div className="flex-1 flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Find..."
            className="flex-1 px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 outline-none focus:border-violet-400 dark:focus:border-violet-500 transition-colors-200"
          />
          <input
            type="text"
            value={replacement}
            onChange={(e) => setReplacement(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Replace with..."
            className="flex-1 px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 outline-none focus:border-violet-400 dark:focus:border-violet-500 transition-colors-200"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1 text-[10px] text-gray-500 dark:text-gray-400 cursor-pointer">
            <input type="checkbox" checked={caseSensitive} onChange={(e) => setCaseSensitive(e.target.checked)} className="w-3 h-3" />
            Aa
          </label>
          <label className="flex items-center gap-1 text-[10px] text-gray-500 dark:text-gray-400 cursor-pointer">
            <input type="checkbox" checked={wholeWord} onChange={(e) => setWholeWord(e.target.checked)} className="w-3 h-3" />
            W
          </label>
          <label className="flex items-center gap-1 text-[10px] text-gray-500 dark:text-gray-400 cursor-pointer">
            <input type="checkbox" checked={useRegex} onChange={(e) => setUseRegex(e.target.checked)} className="w-3 h-3" />
            .*
          </label>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleFind}
            className="px-3 py-1.5 text-xs font-medium bg-violet-500 text-white rounded-lg hover:bg-violet-600 transition-colors-200"
          >
            Find
          </button>
          <button
            onClick={handleReplace}
            disabled={!query}
            className="px-3 py-1.5 text-xs font-medium bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 disabled:opacity-40 transition-colors-200"
          >
            Replace
          </button>
        </div>
      </div>
      {result && (
        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          {result.total_matches > 0
            ? `${result.total_matches} match${result.total_matches !== 1 ? 'es' : ''} found`
            : 'No matches found'}
          {result.replacements_made > 0 && ` · ${result.replacements_made} replaced`}
        </div>
      )}
    </div>
  );
}
