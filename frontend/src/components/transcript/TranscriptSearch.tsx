import { useState, useCallback, useRef, useEffect } from 'react';
import { Search, X } from 'lucide-react';

interface TranscriptSearchProps {
  onSearch: (query: string) => void;
}

export default function TranscriptSearch({ onSearch }: TranscriptSearchProps) {
  const [query, setQuery] = useState('');
  const debounceRef = useRef<number | null>(null);

  const handleChange = useCallback(
    (value: string) => {
      setQuery(value);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = window.setTimeout(() => onSearch(value), 300);
    },
    [onSearch]
  );

  const handleClear = () => {
    setQuery('');
    onSearch('');
  };

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  return (
    <div className="relative flex-1 min-w-[140px] max-w-xs">
      <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
      <input
        type="text"
        value={query}
        onChange={e => handleChange(e.target.value)}
        placeholder="Search transcript..."
        className="w-full pl-8 pr-8 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-300 placeholder-gray-400 dark:placeholder-gray-500 outline-none focus:ring-2 focus:ring-violet-100 dark:focus:ring-violet-900/30 transition-all-200"
      />
      {query && (
        <button
          onClick={handleClear}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <X size={12} />
        </button>
      )}
    </div>
  );
}
