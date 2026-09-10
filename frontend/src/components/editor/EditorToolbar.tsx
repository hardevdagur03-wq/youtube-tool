import { useCallback } from 'react';
import { useEditor } from '../../context/EditorContext';
import type { FormattingCommand, ViewMode } from '../../types/editor';

const TOOLBAR_ITEMS: { icon: string; cmd: FormattingCommand; title: string; dividerAfter?: boolean }[] = [
  { icon: '↩', cmd: 'undo', title: 'Undo (Ctrl+Z)' },
  { icon: '↪', cmd: 'redo', title: 'Redo (Ctrl+Y)' },
  { dividerAfter: true, icon: '', cmd: 'bold', title: '' },
  { icon: 'B', cmd: 'bold', title: 'Bold (Ctrl+B)' },
  { icon: 'I', cmd: 'italic', title: 'Italic (Ctrl+I)' },
  { icon: 'S', cmd: 'strikethrough', title: 'Strikethrough' },
  { icon: '`', cmd: 'inline_code', title: 'Inline Code' },
  { dividerAfter: true, icon: '', cmd: 'bold', title: '' },
  { icon: 'H1', cmd: 'heading_1', title: 'Heading 1' },
  { icon: 'H2', cmd: 'heading_2', title: 'Heading 2' },
  { icon: 'H3', cmd: 'heading_3', title: 'Heading 3' },
  { dividerAfter: true, icon: '', cmd: 'bold', title: '' },
  { icon: '•', cmd: 'bullet_list', title: 'Bullet List' },
  { icon: '1.', cmd: 'ordered_list', title: 'Ordered List' },
  { icon: '❝', cmd: 'blockquote', title: 'Blockquote' },
  { icon: '⌨', cmd: 'code_block', title: 'Code Block' },
  { icon: '—', cmd: 'horizontal_rule', title: 'Horizontal Rule' },
];

const VIEW_MODES: { icon: string; mode: ViewMode; title: string }[] = [
  { icon: '✎', mode: 'edit', title: 'Edit' },
  { icon: '◉', mode: 'preview', title: 'Preview' },
  { icon: '⇔', mode: 'split', title: 'Split' },
];

export default function EditorToolbar() {
  const { state, dispatch, applyFormatting, saveContent } = useEditor();

  const handleFormat = useCallback((cmd: FormattingCommand) => {
    applyFormatting(cmd);
  }, [applyFormatting]);

  const handleSave = useCallback(() => {
    saveContent();
  }, [saveContent]);

  return (
    <div className="flex items-center gap-1 px-3 py-1.5 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 overflow-x-auto">
      <div className="flex items-center gap-1 mr-3">
        {TOOLBAR_ITEMS.map((item, i) =>
          item.dividerAfter ? (
            <div key={i} className="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-1" />
          ) : (
            <button
              key={i}
              onClick={() => handleFormat(item.cmd)}
              title={item.title}
              className="px-1.5 py-1 text-xs font-semibold rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 transition-colors-200"
            >
              {item.icon}
            </button>
          )
        )}
      </div>

      <div className="flex-1" />

      <div className="flex items-center gap-1 mr-3">
        {VIEW_MODES.map((vm) => (
          <button
            key={vm.mode}
            onClick={() => dispatch({ type: 'SET_VIEW_MODE', payload: vm.mode })}
            title={vm.title}
            className={`px-2 py-1 text-xs rounded-md font-medium transition-all-200 ${
              state.viewMode === vm.mode
                ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300'
                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            {vm.icon} {vm.title}
          </button>
        ))}
      </div>

      <div className="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-1" />

      <button
        onClick={() => dispatch({ type: 'TOGGLE_FIND_REPLACE' })}
        title="Find & Replace (Ctrl+F)"
        className={`px-2 py-1 text-xs rounded-md font-medium transition-all-200 ${
          state.findReplaceOpen
            ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300'
            : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'
        }`}
      >
        🔍 Find
      </button>

      <button
        onClick={() => dispatch({ type: 'TOGGLE_AI_PANEL' })}
        title="AI Assistant"
        className={`px-2 py-1 text-xs rounded-md font-medium transition-all-200 ${
          state.aiPanelOpen
            ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300'
            : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'
        }`}
      >
        ✨ AI
      </button>

      <button
        onClick={() => dispatch({ type: 'TOGGLE_VERSION_HISTORY' })}
        title="Version History"
        className={`px-2 py-1 text-xs rounded-md font-medium transition-all-200 ${
          state.versionHistoryOpen
            ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300'
            : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'
        }`}
      >
        📋 History
      </button>

      <button
        onClick={() => dispatch({ type: 'TOGGLE_STATS_PANEL' })}
        title="Document Stats"
        className={`px-2 py-1 text-xs rounded-md font-medium transition-all-200 ${
          state.statsPanelOpen
            ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300'
            : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'
        }`}
      >
        📊 Stats
      </button>

      <div className="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-1" />

      <button
        onClick={handleSave}
        disabled={!state.isDirty || state.isSaving}
        className={`px-3 py-1 text-xs font-semibold rounded-md transition-all-200 ${
          state.isDirty
            ? 'bg-emerald-500 text-white hover:bg-emerald-600 shadow-sm'
            : 'text-gray-400 dark:text-gray-600 cursor-default'
        }`}
      >
        {state.isSaving ? 'Saving...' : state.isDirty ? 'Save' : 'Saved'}
      </button>

      <div className="flex items-center gap-2 ml-2 text-[10px] text-gray-400 dark:text-gray-500">
        {state.isDirty && <span className="w-2 h-2 rounded-full bg-amber-400" />}
        {state.stats && <span>{state.stats.word_count} words</span>}
      </div>
    </div>
  );
}
