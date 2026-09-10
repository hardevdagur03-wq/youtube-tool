import { createContext, useContext, useReducer, useEffect, useCallback, useRef, type ReactNode } from 'react';
import { EditorAPI } from '../services/EditorService';
import type {
  ViewMode, CursorPosition, ScrollPosition, SelectionRange,
  DocumentModel, DocumentStats, HeadingInfo, VersionInfo,
  AIActionRequest, AIActionResponse, FindReplaceRequest, FindReplaceResult,
  TranslationRequest, TranslationResponse, VersionDiff, FormattingCommand,
} from '../types/editor';

interface EditorStateType {
  projectId: string;
  content: string;
  title: string;
  document: DocumentModel | null;
  stats: DocumentStats | null;
  seoScore: number;
  headings: HeadingInfo[];
  versions: VersionInfo[];
  viewMode: ViewMode;
  cursor: CursorPosition;
  selection: SelectionRange;
  scroll: ScrollPosition;
  isDirty: boolean;
  isSaving: boolean;
  isLoading: boolean;
  canUndo: boolean;
  canRedo: boolean;
  lastSavedAt: string;
  error: string | null;
  findReplaceOpen: boolean;
  versionHistoryOpen: boolean;
  aiPanelOpen: boolean;
  statsPanelOpen: boolean;
  headingNavOpen: boolean;
  diffView: { open: boolean; oldVersion: number; newVersion: number; diff: VersionDiff | null };
}

type EditorAction =
  | { type: 'SET_PROJECT_ID'; payload: string }
  | { type: 'SET_CONTENT'; payload: string }
  | { type: 'SET_TITLE'; payload: string }
  | { type: 'SET_DOCUMENT'; payload: DocumentModel }
  | { type: 'SET_STATS'; payload: { stats: DocumentStats; seoScore: number } }
  | { type: 'SET_HEADINGS'; payload: HeadingInfo[] }
  | { type: 'SET_VERSIONS'; payload: VersionInfo[] }
  | { type: 'SET_VIEW_MODE'; payload: ViewMode }
  | { type: 'SET_CURSOR'; payload: CursorPosition }
  | { type: 'SET_SELECTION'; payload: SelectionRange }
  | { type: 'SET_SCROLL'; payload: ScrollPosition }
  | { type: 'SET_DIRTY'; payload: boolean }
  | { type: 'SET_SAVING'; payload: boolean }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_UNDO_REDO'; payload: { canUndo: boolean; canRedo: boolean } }
  | { type: 'SET_LAST_SAVED'; payload: string }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'TOGGLE_FIND_REPLACE' }
  | { type: 'TOGGLE_VERSION_HISTORY' }
  | { type: 'TOGGLE_AI_PANEL' }
  | { type: 'TOGGLE_STATS_PANEL' }
  | { type: 'TOGGLE_HEADING_NAV' }
  | { type: 'SET_DIFF_VIEW'; payload: { open: boolean; oldVersion: number; newVersion: number; diff: VersionDiff | null } }
  | { type: 'LOAD_INITIAL'; payload: { content: string; title: string; stats: DocumentStats; seoScore: number; headings: HeadingInfo[]; versions: VersionInfo[] } };

const initialState: EditorStateType = {
  projectId: '',
  content: '',
  title: '',
  document: null,
  stats: null,
  seoScore: 0,
  headings: [],
  versions: [],
  viewMode: 'split',
  cursor: { line: 0, column: 0, offset: 0 },
  selection: { start: { line: 0, column: 0, offset: 0 }, end: { line: 0, column: 0, offset: 0 }, text: '', collapsed: true },
  scroll: { top: 0, left: 0 },
  isDirty: false,
  isSaving: false,
  isLoading: true,
  canUndo: false,
  canRedo: false,
  lastSavedAt: '',
  error: null,
  findReplaceOpen: false,
  versionHistoryOpen: false,
  aiPanelOpen: false,
  statsPanelOpen: false,
  headingNavOpen: true,
  diffView: { open: false, oldVersion: 0, newVersion: 0, diff: null },
};

function reducer(state: EditorStateType, action: EditorAction): EditorStateType {
  switch (action.type) {
    case 'SET_PROJECT_ID': return { ...state, projectId: action.payload };
    case 'SET_CONTENT': return { ...state, content: action.payload, isDirty: true };
    case 'SET_TITLE': return { ...state, title: action.payload };
    case 'SET_DOCUMENT': return { ...state, document: action.payload };
    case 'SET_STATS': return { ...state, stats: action.payload.stats, seoScore: action.payload.seoScore };
    case 'SET_HEADINGS': return { ...state, headings: action.payload };
    case 'SET_VERSIONS': return { ...state, versions: action.payload };
    case 'SET_VIEW_MODE': return { ...state, viewMode: action.payload };
    case 'SET_CURSOR': return { ...state, cursor: action.payload };
    case 'SET_SELECTION': return { ...state, selection: action.payload };
    case 'SET_SCROLL': return { ...state, scroll: action.payload };
    case 'SET_DIRTY': return { ...state, isDirty: action.payload };
    case 'SET_SAVING': return { ...state, isSaving: action.payload };
    case 'SET_LOADING': return { ...state, isLoading: action.payload };
    case 'SET_UNDO_REDO': return { ...state, canUndo: action.payload.canUndo, canRedo: action.payload.canRedo };
    case 'SET_LAST_SAVED': return { ...state, lastSavedAt: action.payload, isDirty: false };
    case 'SET_ERROR': return { ...state, error: action.payload };
    case 'TOGGLE_FIND_REPLACE': return { ...state, findReplaceOpen: !state.findReplaceOpen };
    case 'TOGGLE_VERSION_HISTORY': return { ...state, versionHistoryOpen: !state.versionHistoryOpen };
    case 'TOGGLE_AI_PANEL': return { ...state, aiPanelOpen: !state.aiPanelOpen };
    case 'TOGGLE_STATS_PANEL': return { ...state, statsPanelOpen: !state.statsPanelOpen };
    case 'TOGGLE_HEADING_NAV': return { ...state, headingNavOpen: !state.headingNavOpen };
    case 'SET_DIFF_VIEW': return { ...state, diffView: action.payload };
    case 'LOAD_INITIAL': return {
      ...state,
      content: action.payload.content,
      title: action.payload.title,
      stats: action.payload.stats,
      seoScore: action.payload.seoScore,
      headings: action.payload.headings,
      versions: action.payload.versions,
      isLoading: false,
    };
    default: return state;
  }
}

interface EditorContextValue {
  state: EditorStateType;
  dispatch: React.Dispatch<EditorAction>;
  loadProject: (projectId: string) => Promise<void>;
  saveContent: () => Promise<void>;
  handleUndo: () => Promise<void>;
  handleRedo: () => Promise<void>;
  executeAI: (req: AIActionRequest) => Promise<AIActionResponse | null>;
  translate: (req: TranslationRequest) => Promise<TranslationResponse | null>;
  findText: (req: FindReplaceRequest) => Promise<FindReplaceResult | null>;
  replaceText: (req: FindReplaceRequest) => Promise<FindReplaceResult | null>;
  createVersion: (label?: string) => Promise<void>;
  restoreVersion: (version: number) => Promise<void>;
  showDiff: (oldVersion: number, newVersion: number) => Promise<void>;
  applyFormatting: (cmd: FormattingCommand) => void;
}

const EditorContext = createContext<EditorContextValue | null>(null);

export function EditorProvider({ projectId, children }: { projectId: string; children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const autosaveTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const contentRef = useRef(state.content);
  contentRef.current = state.content;

  useEffect(() => {
    dispatch({ type: 'SET_PROJECT_ID', payload: projectId });
    loadProject(projectId);
    return () => {
      if (autosaveTimer.current) clearInterval(autosaveTimer.current);
    };
  }, [projectId]);

  useEffect(() => {
    if (!state.isLoading && state.isDirty) {
      if (!autosaveTimer.current) {
        autosaveTimer.current = setInterval(() => {
          if (contentRef.current) {
            EditorAPI.save(projectId, contentRef.current, state.title).catch(() => {});
          }
        }, 30000);
      }
    }
    return () => {
      if (autosaveTimer.current) {
        clearInterval(autosaveTimer.current);
        autosaveTimer.current = null;
      }
    };
  }, [state.isLoading, state.isDirty, projectId]);

  const loadProject = useCallback(async (pid: string) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const data = await EditorAPI.load(pid);
      dispatch({ type: 'LOAD_INITIAL', payload: { content: data.content, title: data.title, stats: data.statistics, seoScore: data.seo_score, headings: data.headings, versions: data.versions } });
    } catch (err: any) {
      dispatch({ type: 'SET_ERROR', payload: err.message });
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  const saveContent = useCallback(async () => {
    if (!state.isDirty) return;
    dispatch({ type: 'SET_SAVING', payload: true });
    try {
      const result = await EditorAPI.save(projectId, state.content, state.title);
      dispatch({ type: 'SET_LAST_SAVED', payload: result.saved_at });
    } catch (err: any) {
      dispatch({ type: 'SET_ERROR', payload: err.message });
    } finally {
      dispatch({ type: 'SET_SAVING', payload: false });
    }
  }, [projectId, state.content, state.title, state.isDirty]);

  const handleUndo = useCallback(async () => {
    try {
      const { content, can_undo, can_redo } = await EditorAPI.undo(projectId);
      dispatch({ type: 'SET_CONTENT', payload: content });
      dispatch({ type: 'SET_UNDO_REDO', payload: { canUndo: can_undo, canRedo: can_redo } });
    } catch {}
  }, [projectId]);

  const handleRedo = useCallback(async () => {
    try {
      const { content, can_undo, can_redo } = await EditorAPI.redo(projectId);
      dispatch({ type: 'SET_CONTENT', payload: content });
      dispatch({ type: 'SET_UNDO_REDO', payload: { canUndo: can_undo, canRedo: can_redo } });
    } catch {}
  }, [projectId]);

  const executeAI = useCallback(async (req: AIActionRequest) => {
    try {
      const { result } = await EditorAPI.executeAI(projectId, req);
      if (result.success && result.modified_text) {
        dispatch({ type: 'SET_CONTENT', payload: state.content.replace(req.text, result.modified_text) });
      }
      return result;
    } catch { return null; }
  }, [projectId, state.content]);

  const translate = useCallback(async (req: TranslationRequest) => {
    try {
      const { result } = await EditorAPI.translate(projectId, req);
      if (result.success && req.scope === 'document' && result.translated_text) {
        dispatch({ type: 'SET_CONTENT', payload: result.translated_text });
      }
      return result;
    } catch { return null; }
  }, [projectId]);

  const findText = useCallback(async (req: FindReplaceRequest) => {
    try {
      const { result } = await EditorAPI.find(projectId, req);
      return result;
    } catch { return null; }
  }, [projectId]);

  const replaceText = useCallback(async (req: FindReplaceRequest) => {
    try {
      const { result } = await EditorAPI.replace(projectId, req);
      if (result.replaced_text) {
        dispatch({ type: 'SET_CONTENT', payload: result.replaced_text });
      }
      return result;
    } catch { return null; }
  }, [projectId]);

  const createVersion = useCallback(async (label?: string) => {
    try {
      const { version } = await EditorAPI.createVersion(projectId, label);
      dispatch({ type: 'SET_VERSIONS', payload: [...state.versions, version] });
    } catch {}
  }, [projectId, state.versions]);

  const restoreVersion = useCallback(async (versionNumber: number) => {
    try {
      const { content } = await EditorAPI.restoreVersion(projectId, versionNumber);
      dispatch({ type: 'SET_CONTENT', payload: content });
    } catch {}
  }, [projectId]);

  const showDiff = useCallback(async (oldVersion: number, newVersion: number) => {
    try {
      const { diff } = await EditorAPI.getDiff(projectId, oldVersion, newVersion);
      dispatch({ type: 'SET_DIFF_VIEW', payload: { open: true, oldVersion, newVersion, diff } });
    } catch {}
  }, [projectId]);

  const applyFormatting = useCallback((cmd: FormattingCommand) => {
    const textarea = document.querySelector('.editor-textarea') as HTMLTextAreaElement;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = state.content.substring(start, end);
    let replacement = selected;

    const fmtMap: Record<string, [string, string]> = {
      bold: ['**', '**'], italic: ['*', '*'], strikethrough: ['~~', '~~'],
      inline_code: ['`', '`'], highlight: ['==', '=='],
    };

    const headingMap: Record<string, string> = {
      heading_1: '# ', heading_2: '## ', heading_3: '### ', heading_4: '#### ',
    };

    if (cmd in fmtMap) {
      const [pre, post] = fmtMap[cmd];
      replacement = pre + selected + post;
    } else if (cmd in headingMap) {
      replacement = headingMap[cmd] + (selected || 'Heading');
    } else if (cmd === 'bullet_list') {
      replacement = (selected || 'item').split('\n').map(l => '- ' + l).join('\n');
    } else if (cmd === 'ordered_list') {
      replacement = (selected || 'item').split('\n').map((l, i) => `${i + 1}. ${l}`).join('\n');
    } else if (cmd === 'blockquote') {
      replacement = selected.split('\n').map(l => '> ' + l).join('\n');
    } else if (cmd === 'code_block') {
      replacement = '```\n' + (selected || 'code') + '\n```';
    } else if (cmd === 'horizontal_rule') {
      replacement = '\n---\n';
    } else if (cmd === 'undo') { handleUndo(); return; }
    else if (cmd === 'redo') { handleRedo(); return; }

    const newContent = state.content.substring(0, start) + replacement + state.content.substring(end);
    dispatch({ type: 'SET_CONTENT', payload: newContent });
  }, [state.content, handleUndo, handleRedo]);

  return (
    <EditorContext.Provider value={{
      state, dispatch, loadProject, saveContent, handleUndo, handleRedo,
      executeAI, translate, findText, replaceText, createVersion,
      restoreVersion, showDiff, applyFormatting,
    }}>
      {children}
    </EditorContext.Provider>
  );
}

export function useEditor() {
  const ctx = useContext(EditorContext);
  if (!ctx) throw new Error('useEditor must be inside EditorProvider');
  return ctx;
}
