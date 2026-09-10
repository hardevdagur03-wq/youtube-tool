import { useRef, useCallback, useEffect } from 'react';
import { useEditor } from '../../context/EditorContext';

const LINE_HEIGHT = 22;

function getLineNumbers(content: string): number[] {
  const lines = content.split('\n');
  return lines.map((_, i) => i + 1);
}

function highlightSyntax(text: string): string {
  const lines = text.split('\n');
  return lines.map(line => {
    let escaped = line
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    if (/^#{1,6}\s/.test(escaped)) {
      const level = escaped.match(/^#+/)?.[0]?.length || 1;
      const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4', '#8b5cf6'];
      escaped = escaped.replace(
        /^(#{1,6})(\s+)(.*)$/,
        `$1$2<span style="color:${colors[level - 1]}">$3</span>`
      );
    }

    escaped = escaped.replace(
      /(\*\*|__)(.*?)\1/g,
      '<strong>$2</strong>'
    );
    escaped = escaped.replace(
      /(\*|_)(.*?)\1/g,
      '<em>$2</em>'
    );
    escaped = escaped.replace(
      /`([^`]+)`/g,
      '<code class="bg-gray-100 dark:bg-gray-800 px-1 rounded text-rose-600 dark:text-rose-400 text-xs">$1</code>'
    );
    escaped = escaped.replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      '<span class="text-blue-600 dark:text-blue-400 underline">$1</span>'
    );
    escaped = escaped.replace(
      /```/g,
      '<span class="text-green-600 dark:text-green-400 font-bold">```</span>'
    );

    return escaped;
  }).join('\n');
}

export default function MarkdownEditor() {
  const { state, dispatch } = useEditor();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const editorRef = useRef<HTMLDivElement>(null);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    dispatch({ type: 'SET_CONTENT', payload: e.target.value });
  }, [dispatch]);

  const handleScroll = useCallback(() => {
    if (textareaRef.current) {
      dispatch({
        type: 'SET_SCROLL',
        payload: { top: textareaRef.current.scrollTop, left: textareaRef.current.scrollLeft },
      });
    }
  }, [dispatch]);

  const handleSelect = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    const text = state.content;
    const before = text.substring(0, ta.selectionStart);
    const line = before.split('\n').length;
    const lastNewline = before.lastIndexOf('\n');
    const column = ta.selectionStart - lastNewline;
    dispatch({
      type: 'SET_CURSOR',
      payload: { line, column, offset: ta.selectionStart },
    });
    dispatch({
      type: 'SET_SELECTION',
      payload: {
        start: { line, column, offset: ta.selectionStart },
        end: { line: 0, column: 0, offset: ta.selectionEnd },
        text: text.substring(ta.selectionStart, ta.selectionEnd),
        collapsed: ta.selectionStart === ta.selectionEnd,
      },
    });
  }, [state.content, dispatch]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
      e.preventDefault();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
      e.preventDefault();
    }
  }, []);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  const lines = state.content.split('\n');
  const lineCount = lines.length;

  return (
    <div className="relative h-full flex" ref={editorRef}>
      <div
        className="select-none text-right pr-3 pt-[9px] text-xs leading-[22px] font-mono text-gray-400 dark:text-gray-600 border-r border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 overflow-hidden"
        style={{ minWidth: 48, width: Math.max(48, lineCount.toString().length * 12 + 24) }}
      >
        {getLineNumbers(state.content).map(n => (
          <div key={n}>{n}</div>
        ))}
      </div>
      <div className="relative flex-1">
        <textarea
          ref={textareaRef}
          value={state.content}
          onChange={handleChange}
          onScroll={handleScroll}
          onSelect={handleSelect}
          onKeyDown={handleKeyDown}
          className="editor-textarea absolute inset-0 w-full h-full resize-none bg-transparent text-transparent caret-gray-800 dark:caret-gray-200 font-mono text-sm leading-[22px] p-2.5 outline-none overflow-auto"
          spellCheck={false}
          style={{ tabSize: 4 }}
        />
        <div
          className="pointer-events-none w-full h-full font-mono text-sm leading-[22px] p-2.5 overflow-hidden whitespace-pre-wrap break-words"
          style={{ minHeight: '100%' }}
        >
          {lines.map((line, i) => (
            <div key={i} dangerouslySetInnerHTML={{ __html: highlightSyntax(line) || ' ' }} />
          ))}
        </div>
      </div>
    </div>
  );
}
