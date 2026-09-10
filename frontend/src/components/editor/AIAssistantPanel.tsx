import { useState, useCallback } from 'react';
import { useEditor } from '../../context/EditorContext';
import type { AIActionType } from '../../types/editor';

const AI_ACTIONS: { type: AIActionType; label: string; icon: string; description: string }[] = [
  { type: 'rewrite', label: 'Rewrite', icon: '✎', description: 'Rewrite selected text with improved style' },
  { type: 'expand', label: 'Expand', icon: '⊕', description: 'Add more details and depth' },
  { type: 'simplify', label: 'Simplify', icon: '◊', description: 'Make text easier to read' },
  { type: 'shorten', label: 'Shorten', icon: '⊖', description: 'Condense while keeping key info' },
  { type: 'fix_grammar', label: 'Fix Grammar', icon: '✓', description: 'Correct grammar and spelling' },
  { type: 'improve_tone', label: 'Improve Tone', icon: '♯', description: 'Adjust tone and voice' },
  { type: 'improve_seo', label: 'Improve SEO', icon: '◎', description: 'Optimize for search engines' },
  { type: 'improve_readability', label: 'Improve Readability', icon: '📖', description: 'Make content more readable' },
  { type: 'improve_clarity', label: 'Improve Clarity', icon: '◆', description: 'Make message clearer' },
  { type: 'summarize', label: 'Summarize', icon: '▣', description: 'Create a concise summary' },
  { type: 'continue_writing', label: 'Continue', icon: '→', description: 'Continue writing from cursor' },
  { type: 'generate_examples', label: 'Examples', icon: '¶', description: 'Generate relevant examples' },
  { type: 'explain', label: 'Explain', icon: '?', description: 'Explain in simple terms' },
];

export default function AIAssistantPanel() {
  const { state, dispatch, executeAI } = useEditor();
  const [selectedText, setSelectedText] = useState('');
  const [instructions, setInstructions] = useState('');
  const [tone, setTone] = useState('professional');
  const [loading, setLoading] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const handleAIAction = useCallback(async (type: AIActionType) => {
    const text = state.selection.text || state.content.substring(0, 1000);
    if (!text) return;
    setLoading(type);
    setResult(null);
    const response = await executeAI({
      action_type: type,
      text,
      instructions,
      tone,
    });
    setLoading(null);
    if (response?.success && response.modified_text) {
      setResult(response.modified_text);
    }
  }, [state.content, state.selection.text, instructions, tone, executeAI]);

  if (!state.aiPanelOpen) return null;

  return (
    <div className="w-72 border-l border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-y-auto flex-shrink-0">
      <div className="p-3 border-b border-gray-100 dark:border-gray-800">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-1.5">
          ✨ AI Assistant
        </h3>
        <p className="text-[10px] text-gray-400 mt-0.5">
          Select text or use full document
        </p>
      </div>

      <div className="p-3 space-y-2">
        <textarea
          value={selectedText || state.selection.text}
          onChange={(e) => setSelectedText(e.target.value)}
          placeholder="Selected text appears here..."
          className="w-full h-20 px-3 py-2 text-xs border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 outline-none resize-none focus:border-violet-400 transition-colors-200"
        />

        <select
          value={tone}
          onChange={(e) => setTone(e.target.value)}
          className="w-full px-3 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 outline-none focus:border-violet-400 transition-colors-200"
        >
          <option value="professional">Professional</option>
          <option value="conversational">Conversational</option>
          <option value="academic">Academic</option>
          <option value="persuasive">Persuasive</option>
          <option value="casual">Casual</option>
          <option value="technical">Technical</option>
        </select>

        <input
          type="text"
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          placeholder="Custom instructions..."
          className="w-full px-3 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 outline-none focus:border-violet-400 transition-colors-200"
        />
      </div>

      <div className="px-3 pb-3 grid grid-cols-2 gap-1.5">
        {AI_ACTIONS.map((action) => (
          <button
            key={action.type}
            onClick={() => handleAIAction(action.type)}
            disabled={loading !== null}
            title={action.description}
            className={`flex items-center gap-1.5 px-2 py-1.5 text-[11px] font-medium rounded-lg transition-all-200 ${
              loading === action.type
                ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 animate-pulse'
                : 'bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-800 dark:hover:text-gray-200'
            }`}
          >
            <span>{action.icon}</span>
            <span>{action.label}</span>
          </button>
        ))}
      </div>

      {result && (
        <div className="mx-3 mb-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Result</span>
            <button
              onClick={() => {
                if (state.selection.text) {
                  const newContent = state.content.replace(state.selection.text, result);
                  dispatch({ type: 'SET_CONTENT', payload: newContent });
                }
                setResult(null);
              }}
              className="text-[10px] text-violet-500 hover:text-violet-600 font-medium"
            >
              Apply
            </button>
          </div>
          <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">{result}</p>
        </div>
      )}
    </div>
  );
}
