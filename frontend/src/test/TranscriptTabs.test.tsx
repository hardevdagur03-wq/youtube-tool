import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import type { TranscriptResult } from '../types';
import { useTranscriptTabs } from '../components/transcript/TranscriptTabs';

function makeTranscript(
  overrides: Partial<TranscriptResult> = {},
): TranscriptResult {
  return {
    success: true,
    video_id: 'test1234567',
    source: 'auto',
    provider: 'youtube_auto',
    language: 'en',
    language_confidence: null,
    segments: [{ start: 0, end: 1, duration: 1, text: 'Hello' }],
    plain_text: 'Hello',
    paragraph_text: 'Hello',
    word_count: 1,
    character_count: 5,
    estimated_read_time: '< 1 min',
    generated_at: new Date().toISOString(),
    duration_seconds: null,
    whisper_info: null,
    pipeline_steps: [],
    available_languages: [],
    translation_source: null,
    error: null,
    ...overrides,
  };
}

describe('useTranscriptTabs', () => {
  it('should create manual tab as disabled when no manual transcript', () => {
    const auto = makeTranscript({ source: 'auto', language: 'en' });
    const tabs = renderHook(() => useTranscriptTabs(null, auto, {})).result
      .current;

    const manualTab = tabs.find((t) => t.source === 'manual');
    expect(manualTab).toBeDefined();
    expect(manualTab!.available).toBe(false);
  });

  it('should create auto tab as disabled when no auto transcript', () => {
    const manual = makeTranscript({ source: 'manual', language: 'en' });
    const tabs = renderHook(() => useTranscriptTabs(manual, null, {})).result
      .current;

    const manualTab = tabs.find((t) => t.source === 'manual');
    expect(manualTab).toBeDefined();
    expect(manualTab!.available).toBe(true);

    const autoTab = tabs.find((t) => t.source === 'auto');
    expect(autoTab).toBeDefined();
    expect(autoTab!.available).toBe(false);
  });

  it('should create both tabs when both transcripts exist', () => {
    const manual = makeTranscript({ source: 'manual', language: 'en' });
    const auto = makeTranscript({ source: 'auto', language: 'en' });
    const tabs = renderHook(() => useTranscriptTabs(manual, auto, {})).result
      .current;

    const manualTab = tabs.find((t) => t.source === 'manual');
    expect(manualTab).toBeDefined();
    expect(manualTab!.available).toBe(true);

    const autoTab = tabs.find((t) => t.source === 'auto');
    expect(autoTab).toBeDefined();
    expect(autoTab!.available).toBe(true);
  });

  it('should add translated languages from translations cache', () => {
    const auto = makeTranscript({ source: 'auto', language: 'en' });
    const translated: TranscriptResult = makeTranscript({
      language: 'hi',
      translation_source: 'en',
    });
    const tabs = renderHook(() =>
      useTranscriptTabs(null, auto, { hi: translated }),
    ).result.current;

    const hiTab = tabs.find((t) => t.key === 'hi');
    expect(hiTab).toBeDefined();
    expect(hiTab!.available).toBe(true);
  });

  it('should include available languages from transcript', () => {
    const auto = makeTranscript({
      source: 'auto',
      language: 'en',
      available_languages: [
        { language: 'English', language_code: 'en', is_generated: true, is_translatable: true },
        { language: 'Spanish', language_code: 'es', is_generated: true, is_translatable: true },
        { language: 'French', language_code: 'fr', is_generated: true, is_translatable: true },
      ],
    });
    const tabs = renderHook(() => useTranscriptTabs(null, auto, {})).result
      .current;

    expect(tabs.some((t) => t.languageCode === 'es')).toBe(true);
    expect(tabs.some((t) => t.languageCode === 'fr')).toBe(true);
  });
});
