import { useCallback, useEffect } from 'react';
import { EditorProvider, useEditor } from '../../context/EditorContext';
import EditorToolbar from './EditorToolbar';
import MarkdownEditor from './MarkdownEditor';
import LivePreview from './LivePreview';
import SplitView from './SplitView';
import FindReplacePanel from './FindReplacePanel';
import AIAssistantPanel from './AIAssistantPanel';
import HeadingNavigator from './HeadingNavigator';
import VersionHistoryPanel from './VersionHistory';
import DocumentStatsPanel from './DocumentStats';

function EditorInner() {
  const { state, dispatch, saveContent, handleUndo, handleRedo } = useEditor();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveContent();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        handleUndo();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        e.preventDefault();
        handleRedo();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault();
        dispatch({ type: 'TOGGLE_FIND_REPLACE' });
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'i') {
        e.preventDefault();
      }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'P') {
        e.preventDefault();
        dispatch({ type: 'TOGGLE_AI_PANEL' });
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [saveContent, handleUndo, handleRedo, dispatch]);

  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (state.isDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [state.isDirty]);

  if (state.isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-gray-400">Loading editor...</span>
        </div>
      </div>
    );
  }

  if (state.error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <p className="text-red-500 font-medium">Error loading editor</p>
          <p className="text-sm text-gray-400 mt-1">{state.error}</p>
          <button
            onClick={() => dispatch({ type: 'SET_ERROR', payload: null })}
            className="mt-3 px-4 py-2 text-sm font-medium text-violet-600 hover:text-violet-700 transition-colors-200"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-card overflow-hidden">
      <EditorToolbar />
      <FindReplacePanel />
      <div className="flex flex-1 min-h-0">
        <HeadingNavigator />
        <div className="flex-1 min-w-0">
          {state.viewMode === 'edit' && (
            <div className="h-full overflow-auto">
              <MarkdownEditor />
            </div>
          )}
          {state.viewMode === 'preview' && <LivePreview />}
          {state.viewMode === 'split' && <SplitView />}
          {state.viewMode === 'rich_text' && (
            <div className="h-full overflow-auto p-6">
              <p className="text-center text-gray-400 text-sm py-12">
                Rich text editing will be available in full editor mode.
                Switch to Split View for Markdown + Preview.
              </p>
            </div>
          )}
          {state.viewMode === 'source' && (
            <div className="h-full overflow-auto">
              <MarkdownEditor />
            </div>
          )}
        </div>
        <AIAssistantPanel />
        <VersionHistoryPanel />
        <DocumentStatsPanel />
      </div>
      <div className="px-4 py-1.5 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between text-[10px] text-gray-400 dark:text-gray-500">
        <div className="flex items-center gap-3">
          <span>Ln {state.cursor.line}, Col {state.cursor.column}</span>
          <span>Words: {state.stats?.word_count || 0}</span>
          <span>Chars: {state.stats?.character_count || 0}</span>
        </div>
        <div className="flex items-center gap-3">
          {state.isSaving && <span>Saving...</span>}
          {state.lastSavedAt && <span>Saved {new Date(state.lastSavedAt).toLocaleTimeString()}</span>}
          <span className={`px-1.5 py-0.5 rounded ${state.isDirty ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300' : 'text-gray-400'}`}>
            {state.isDirty ? 'Unsaved' : 'Saved'}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function EditorContainer({ projectId }: { projectId: string }) {
  return (
    <EditorProvider projectId={projectId}>
      <EditorInner />
    </EditorProvider>
  );
}
