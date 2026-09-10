import { useReducer, useCallback } from 'react';
import type { TranscriptResult } from '../types';
import { transcriptService } from '../services/TranscriptService';

interface TranscriptState {
  videoId: string | null;
  original: TranscriptResult | null;
  translations: Record<string, TranscriptResult>;
  selectedLanguage: string;
  loading: boolean;
  error: string | null;
}

type TranscriptAction =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; payload: { videoId: string; transcript: TranscriptResult } }
  | { type: 'FETCH_ERROR'; payload: string }
  | { type: 'SET_SELECTED_LANGUAGE'; payload: string }
  | { type: 'SET_TRANSLATION'; payload: { language: string; transcript: TranscriptResult } }
  | { type: 'TRANSLATE_START' }
  | { type: 'RESET' };

const initialState: TranscriptState = {
  videoId: null,
  original: null,
  translations: {},
  selectedLanguage: 'en',
  loading: false,
  error: null,
};

function reducer(state: TranscriptState, action: TranscriptAction): TranscriptState {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, loading: true, error: null };
    case 'FETCH_SUCCESS':
      return {
        ...state,
        videoId: action.payload.videoId,
        original: action.payload.transcript,
        selectedLanguage: action.payload.transcript.language,
        loading: false,
        error: null,
        translations: {},
      };
    case 'FETCH_ERROR':
      return { ...state, loading: false, error: action.payload };
    case 'SET_SELECTED_LANGUAGE':
      return { ...state, selectedLanguage: action.payload };
    case 'SET_TRANSLATION':
      return {
        ...state,
        translations: {
          ...state.translations,
          [action.payload.language]: action.payload.transcript,
        },
        selectedLanguage: action.payload.language,
      };
    case 'TRANSLATE_START':
      return state;
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

export function useTranscriptStore() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const fetchTranscript = useCallback(async (videoId: string) => {
    dispatch({ type: 'FETCH_START' });
    try {
      const transcript = await transcriptService.fetchTranscript(videoId);
      dispatch({ type: 'FETCH_SUCCESS', payload: { videoId, transcript } });
    } catch (err) {
      dispatch({
        type: 'FETCH_ERROR',
        payload: err instanceof Error ? err.message : 'Failed to fetch transcript',
      });
    }
  }, []);

  const selectLanguage = useCallback((lang: string) => {
    dispatch({ type: 'SET_SELECTED_LANGUAGE', payload: lang });
  }, []);

  const translate = useCallback(async (targetLang: string) => {
    if (!state.videoId || !state.original) return;

    const existing = state.translations[targetLang];
    if (existing) {
      dispatch({ type: 'SET_SELECTED_LANGUAGE', payload: targetLang });
      return;
    }

    if (targetLang === state.original.language) {
      dispatch({ type: 'SET_SELECTED_LANGUAGE', payload: targetLang });
      return;
    }

    const cached = transcriptService.getCachedTranslation(state.videoId, targetLang);
    if (cached) {
      dispatch({ type: 'SET_TRANSLATION', payload: { language: targetLang, transcript: cached } });
      return;
    }

    dispatch({ type: 'TRANSLATE_START' });
    try {
      const translated = await transcriptService.translateTranscript(state.videoId, targetLang);
      dispatch({ type: 'SET_TRANSLATION', payload: { language: targetLang, transcript: translated } });
    } catch {
      dispatch({ type: 'SET_SELECTED_LANGUAGE', payload: state.selectedLanguage });
    }
  }, [state.videoId, state.original, state.translations, state.selectedLanguage]);

  const getActiveTranscript = useCallback((): TranscriptResult | null => {
    if (!state.original) return null;
    if (state.selectedLanguage === state.original.language) return state.original;
    return state.translations[state.selectedLanguage] || state.original;
  }, [state.original, state.translations, state.selectedLanguage]);

  const reset = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, []);

  return {
    ...state,
    fetchTranscript,
    selectLanguage,
    translate,
    getActiveTranscript,
    reset,
  };
}
