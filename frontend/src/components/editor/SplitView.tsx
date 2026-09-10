import { useRef, useState, useCallback, useEffect } from 'react';
import MarkdownEditor from './MarkdownEditor';
import LivePreview from './LivePreview';

export default function SplitView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [splitPercent, setSplitPercent] = useState(50);
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const pct = Math.max(20, Math.min(80, (x / rect.width) * 100));
    setSplitPercent(pct);
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return (
    <div ref={containerRef} className="flex h-full relative">
      <div className="h-full overflow-hidden border-r border-gray-200 dark:border-gray-700" style={{ width: `${splitPercent}%` }}>
        <div className="h-full overflow-auto">
          <MarkdownEditor />
        </div>
      </div>
      <div
        className="absolute top-0 bottom-0 w-1.5 bg-gray-200 dark:bg-gray-700 hover:bg-violet-400 dark:hover:bg-violet-500 cursor-col-resize z-10 transition-colors-200 flex items-center justify-center group"
        style={{ left: `calc(${splitPercent}% - 3px)` }}
        onMouseDown={handleMouseDown}
      >
        <div className="w-0.5 h-8 bg-gray-400 dark:bg-gray-500 rounded-full group-hover:bg-white transition-colors-200" />
      </div>
      <div className="flex-1 h-full overflow-hidden" style={{ width: `${100 - splitPercent}%` }}>
        <div className="h-full overflow-auto">
          <LivePreview />
        </div>
      </div>
    </div>
  );
}
