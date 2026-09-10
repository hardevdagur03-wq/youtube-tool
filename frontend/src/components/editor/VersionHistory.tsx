import { useState, useCallback } from 'react';
import { useEditor } from '../../context/EditorContext';
import type { VersionInfo, VersionDiff } from '../../types/editor';

function DiffRenderer({ diff }: { diff: VersionDiff }) {
  return (
    <div className="font-mono text-xs leading-5">
      <div className="flex items-center gap-3 px-3 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 text-xs text-gray-500">
        <span>v{diff.old_version} → v{diff.new_version}</span>
        <span className="text-green-600">+{diff.added_lines}</span>
        <span className="text-red-600">-{diff.removed_lines}</span>
        <span>{diff.change_percentage}% changed</span>
      </div>
      <div className="max-h-96 overflow-y-auto">
        {diff.lines.map((line, i) => {
          const cls = line.type === 'added'
            ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200'
            : line.type === 'removed'
              ? 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200'
              : 'text-gray-600 dark:text-gray-400';
          const prefix = line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' ';
          return (
            <div key={i} className={`flex ${cls}`}>
              <span className="w-10 text-right pr-2 text-gray-400 select-none">{line.old_line_number || ''}</span>
              <span className="w-10 text-right pr-2 text-gray-400 select-none">{line.new_line_number || ''}</span>
              <span className="w-4 text-center select-none text-gray-400">{prefix}</span>
              <span className="flex-1 whitespace-pre-wrap">{line.content}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function VersionHistoryPanel() {
  const { state, dispatch, createVersion, restoreVersion, showDiff } = useEditor();
  const [diffLoading, setDiffLoading] = useState(false);

  const handleRestore = useCallback(async (version: VersionInfo) => {
    await restoreVersion(version.version_number);
    dispatch({ type: 'SET_DIFF_VIEW', payload: { open: false, oldVersion: 0, newVersion: 0, diff: null } });
  }, [restoreVersion, dispatch]);

  const handleCompare = useCallback(async (v: VersionInfo) => {
    setDiffLoading(true);
    const idx = state.versions.indexOf(v);
    if (idx > 0) {
      await showDiff(state.versions[idx - 1].version_number, v.version_number);
    }
    setDiffLoading(false);
  }, [state.versions, showDiff]);

  if (!state.versionHistoryOpen && !state.diffView.open) return null;

  return (
    <div className="w-72 border-l border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-y-auto flex-shrink-0">
      {state.diffView.open && state.diffView.diff ? (
        <div>
          <div className="flex items-center justify-between p-3 border-b border-gray-100 dark:border-gray-800">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Diff View</h3>
            <button
              onClick={() => dispatch({ type: 'SET_DIFF_VIEW', payload: { open: false, oldVersion: 0, newVersion: 0, diff: null } })}
              className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              ×
            </button>
          </div>
          <DiffRenderer diff={state.diffView.diff} />
        </div>
      ) : state.versionHistoryOpen ? (
        <div>
          <div className="p-3 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Version History</h3>
              <p className="text-[10px] text-gray-400">{state.versions.length} versions</p>
            </div>
            <button
              onClick={() => createVersion()}
              className="px-2.5 py-1 text-[10px] font-medium bg-violet-500 text-white rounded-lg hover:bg-violet-600 transition-colors-200"
            >
              + Save
            </button>
          </div>
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {state.versions.length === 0 ? (
              <p className="p-3 text-[11px] text-gray-400 italic">No versions yet</p>
            ) : (
              [...state.versions].reverse().map((v) => (
                <div key={v.version_number} className="p-3 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors-200">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-gray-900 dark:text-white">
                      v{v.version_number}
                    </span>
                    <span className="text-[10px] text-gray-400">
                      {new Date(v.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {v.label && (
                    <p className="text-[11px] text-gray-500 dark:text-gray-400 truncate">{v.label}</p>
                  )}
                  <p className="text-[10px] text-gray-400">
                    {v.word_count} words · {v.is_automatic ? 'Auto' : 'Manual'}
                    {v.is_checkpoint && ' · Checkpoint'}
                  </p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <button
                      onClick={() => handleRestore(v)}
                      className="text-[10px] text-violet-500 hover:text-violet-600 font-medium"
                    >
                      Restore
                    </button>
                    <button
                      onClick={() => handleCompare(v)}
                      disabled={diffLoading}
                      className="text-[10px] text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 font-medium"
                    >
                      Compare
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
