import { createContext, useContext, useReducer, useEffect, type ReactNode } from 'react';
import type { WorkflowState, WorkflowStep, VideoMetadataResponse, VideoMetadata, TranscriptResult, ProcessingResult, ContentAnalysisResult } from '../types';

const STORAGE_KEY = 'yt_blog_workflow';

const initialState: WorkflowState = {
  currentStep: 'url',
  videoId: null,
  normalizedUrl: null,
  metadata: null,
  metadataResponse: null,
  transcript: null,
  translatedTranscripts: {},
  selectedLanguage: 'en',
  processedTranscript: null,
  processingStatus: 'idle',
  analysis: null,
  analysisStatus: 'idle',
  stepStatus: {
    url: 'pending',
    metadata: 'pending',
    transcript: 'pending',
    analysis: 'pending',
    generate: 'pending',
    editor: 'pending',
    export: 'pending',
  },
  error: null,
};

type Action =
  | { type: 'SET_STEP'; payload: WorkflowStep }
  | { type: 'SET_VIDEO'; payload: { videoId: string; normalizedUrl: string } }
  | { type: 'SET_METADATA'; payload: VideoMetadataResponse }
  | { type: 'SET_TRANSCRIPT'; payload: TranscriptResult }
  | { type: 'SET_TRANSLATED_TRANSCRIPT'; payload: { language: string; transcript: TranscriptResult } }
  | { type: 'SET_SELECTED_LANGUAGE'; payload: string }
  | { type: 'SET_PROCESSED_TRANSCRIPT'; payload: { result: ProcessingResult; status: WorkflowState['processingStatus'] } }
  | { type: 'SET_PROCESSING_STATUS'; payload: WorkflowState['processingStatus'] }
  | { type: 'SET_ANALYSIS'; payload: { result: ContentAnalysisResult; status: WorkflowState['analysisStatus'] } }
  | { type: 'SET_ANALYSIS_STATUS'; payload: WorkflowState['analysisStatus'] }
  | { type: 'SET_STEP_STATUS'; payload: { step: WorkflowStep; status: WorkflowState['stepStatus'][WorkflowStep] } }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'RESTORE'; payload: WorkflowState }
  | { type: 'RESET' };

function reducer(state: WorkflowState, action: Action): WorkflowState {
  switch (action.type) {
    case 'SET_STEP':
      return { ...state, currentStep: action.payload };
    case 'SET_VIDEO':
      return {
        ...state,
        videoId: action.payload.videoId,
        normalizedUrl: action.payload.normalizedUrl,
        stepStatus: { ...state.stepStatus, url: 'ok' },
      };
    case 'SET_METADATA': {
      const meta = action.payload;
      return {
        ...state,
        metadataResponse: meta,
        metadata: meta.video,
        stepStatus: { ...state.stepStatus, metadata: meta.success ? 'ok' : 'error' },
        error: meta.success ? null : meta.error || null,
      };
    }
    case 'SET_TRANSCRIPT':
      return {
        ...state,
        transcript: action.payload,
        selectedLanguage: action.payload.language === 'hi' ? 'en' : action.payload.language,
        stepStatus: { ...state.stepStatus, transcript: action.payload.success ? 'ok' : 'error' },
      };
    case 'SET_TRANSLATED_TRANSCRIPT':
      return {
        ...state,
        translatedTranscripts: {
          ...state.translatedTranscripts,
          [action.payload.language]: action.payload.transcript,
        },
      };
    case 'SET_SELECTED_LANGUAGE':
      return { ...state, selectedLanguage: action.payload };
    case 'SET_PROCESSED_TRANSCRIPT':
      return {
        ...state,
        processedTranscript: action.payload.result,
        processingStatus: action.payload.status,
        stepStatus: {
          ...state.stepStatus,
          transcript: action.payload.status === 'ok' ? 'ok' : state.stepStatus.transcript,
        },
      };
    case 'SET_PROCESSING_STATUS':
      return { ...state, processingStatus: action.payload };
    case 'SET_ANALYSIS':
      return {
        ...state,
        analysis: action.payload.result,
        analysisStatus: action.payload.status,
        stepStatus: { ...state.stepStatus, analysis: action.payload.status === 'ok' ? 'ok' : state.stepStatus.analysis },
      };
    case 'SET_ANALYSIS_STATUS':
      return { ...state, analysisStatus: action.payload };
    case 'SET_STEP_STATUS':
      return {
        ...state,
        stepStatus: { ...state.stepStatus, [action.payload.step]: action.payload.status },
      };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'RESTORE':
      return { ...action.payload };
    case 'RESET':
      return { ...initialState };
    default:
      return state;
  }
}

interface WorkflowContextValue {
  state: WorkflowState;
  dispatch: React.Dispatch<Action>;
  goToStep: (step: WorkflowStep) => void;
  reset: () => void;
}

const WorkflowContext = createContext<WorkflowContextValue | null>(null);

export function WorkflowProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState, () => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return { ...initialState, ...parsed };
      }
    } catch {
      // ignore
    }
    return initialState;
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // ignore
    }
  }, [state]);

  const goToStep = (step: WorkflowStep) => {
    dispatch({ type: 'SET_STEP', payload: step });
  };

  const reset = () => {
    localStorage.removeItem(STORAGE_KEY);
    dispatch({ type: 'RESET' });
  };

  return (
    <WorkflowContext.Provider value={{ state, dispatch, goToStep, reset }}>
      {children}
    </WorkflowContext.Provider>
  );
}

export function useWorkflow() {
  const ctx = useContext(WorkflowContext);
  if (!ctx) throw new Error('useWorkflow must be inside WorkflowProvider');
  return ctx;
}
