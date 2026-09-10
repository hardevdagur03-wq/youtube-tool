import { useMemo, useState } from 'react';
import { useEditor } from '../../context/EditorContext';
import type { HeadingInfo } from '../../types/editor';

function buildTree(headings: HeadingInfo[]): HeadingInfo[] {
  const tree: HeadingInfo[] = [];
  const stack: HeadingInfo[] = [];
  for (const h of headings) {
    const node = { ...h, children: [] };
    while (stack.length > 0 && stack[stack.length - 1].level >= h.level) {
      stack.pop();
    }
    if (stack.length > 0) {
      if (!stack[stack.length - 1].children) stack[stack.length - 1].children = [];
      (stack[stack.length - 1].children as HeadingInfo[]).push(node);
    } else {
      tree.push(node);
    }
    stack.push(node);
  }
  return tree;
}

function HeadingTree({ items, level = 0 }: { items: HeadingInfo[]; level?: number }) {
  const { state, dispatch } = useEditor();
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

  const toggleCollapse = (text: string) => {
    setCollapsed(prev => {
      const next = new Set(prev);
      if (next.has(text)) next.delete(text);
      else next.add(text);
      return next;
    });
  };

  return (
    <ul className={`space-y-0.5 ${level > 0 ? 'ml-3 border-l border-gray-100 dark:border-gray-800 pl-2' : ''}`}>
      {items.map((heading) => {
        const isCollapsed = collapsed.has(heading.text);
        const hasChildren = heading.children && heading.children.length > 0;
        const isActive = state.content.split('\n')[heading.line - 1]?.includes(heading.text);

        return (
          <li key={heading.text + heading.line}>
            <div className="flex items-center gap-0.5 group">
              {hasChildren && (
                <button
                  onClick={() => toggleCollapse(heading.text)}
                  className="w-3.5 h-3.5 flex items-center justify-center text-[8px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors-200"
                >
                  {isCollapsed ? '▶' : '▼'}
                </button>
              )}
              {!hasChildren && <span className="w-3.5" />}
              <button
                onClick={() => dispatch({
                  type: 'SET_SCROLL',
                  payload: { top: (heading.line - 1) * 22, left: 0 },
                })}
                className={`flex-1 text-left truncate rounded transition-colors-200 ${
                  level === 0 ? 'text-xs font-semibold' : 'text-[11px]'
                } ${isActive ? 'text-violet-600 dark:text-violet-400' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}`}
                title={heading.text}
              >
                <span className="opacity-40 mr-1">{heading.tag.toUpperCase()}</span>
                {heading.text}
              </button>
            </div>
            {hasChildren && !isCollapsed && (
              <HeadingTree items={heading.children as HeadingInfo[]} level={level + 1} />
            )}
          </li>
        );
      })}
    </ul>
  );
}

export default function HeadingNavigator() {
  const { state } = useEditor();
  const headingTree = useMemo(() => buildTree(state.headings), [state.headings]);

  if (!state.headingNavOpen) return null;

  return (
    <div className="w-56 border-r border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 overflow-y-auto flex-shrink-0">
      <div className="p-3 border-b border-gray-100 dark:border-gray-800">
        <h3 className="text-xs font-semibold text-gray-900 dark:text-white flex items-center gap-1.5">
          ☰ Outline
        </h3>
        <p className="text-[10px] text-gray-400 mt-0.5">{state.headings.length} headings</p>
      </div>
      <div className="p-3">
        {state.headings.length === 0 ? (
          <p className="text-[11px] text-gray-400 italic">No headings found</p>
        ) : (
          <HeadingTree items={headingTree} />
        )}
      </div>
    </div>
  );
}
