import { useMemo } from 'react';
import type { TranscriptResult, TranscriptTab } from '../../types';
import { getLanguageLabel } from '../../types';
import LanguageSelector from './LanguageSelector';

interface TranscriptTabsProps {
  transcript: TranscriptResult;
  manualTranscript: TranscriptResult | null;
  autoTranscript: TranscriptResult | null;
  whisperTranscript: TranscriptResult | null;
  translatedTranscripts: Record<string, TranscriptResult>;
  selectedLanguage: string;
  onLanguageChange: (language: string) => Promise<void>;
  isTranslating?: boolean;
}

export function useTranscriptTabs(
  manualTranscript: TranscriptResult | null,
  autoTranscript: TranscriptResult | null,
  translatedTranscripts: Record<string, TranscriptResult>,
  whisperTranscript: TranscriptResult | null = null,
): TranscriptTab[] {
  return useMemo(() => {
    const tabs: TranscriptTab[] = [];
    const seen = new Set<string>();

    // Manual tab
    if (manualTranscript) {
      tabs.push({
        key: manualTranscript.language,
        label: 'Manual',
        source: 'manual',
        available: true,
        language: manualTranscript.language,
        languageCode: manualTranscript.language,
      });
      seen.add(manualTranscript.language);
    } else {
      tabs.push({
        key: 'manual',
        label: 'Manual',
        source: 'manual',
        available: false,
        language: 'Manual',
        languageCode: '',
      });
    }

    // Auto tab (original language)
    if (autoTranscript) {
      const code = autoTranscript.language;
      tabs.push({
        key: code,
        label: 'Auto',
        source: 'auto',
        available: true,
        language: code,
        languageCode: code,
      });
      seen.add(code);
    } else {
      tabs.push({
        key: 'auto',
        label: 'Auto',
        source: 'auto',
        available: false,
        language: 'Auto',
        languageCode: '',
      });
    }

    // Whisper tab
    if (whisperTranscript) {
      const code = whisperTranscript.language;
      tabs.push({
        key: code,
        label: 'Whisper',
        source: 'whisper',
        available: true,
        language: code,
        languageCode: code,
      });
      seen.add(code);
    }

    // Other available languages from the transcript's available_languages list
    // (these would be for translation)
    const availableLangs = autoTranscript?.available_languages ||
      manualTranscript?.available_languages ||
      whisperTranscript?.available_languages || [];
    for (const lang of availableLangs) {
      const code = lang.language_code;
      if (seen.has(code)) continue;
      seen.add(code);

      tabs.push({
        key: code,
        label: getLanguageLabel(code),
        source: lang.is_generated ? 'auto' : 'manual',
        available: true,
        language: lang.language,
        languageCode: code,
      });
    }

    // Translated languages already cached
    for (const code of Object.keys(translatedTranscripts)) {
      if (seen.has(code)) continue;
      seen.add(code);
      tabs.push({
        key: code,
        label: getLanguageLabel(code),
        source: 'translated',
        available: true,
        language: getLanguageLabel(code),
        languageCode: code,
      });
    }

    console.log(`[TranscriptTabs] Generated ${tabs.length} tabs:`, tabs.map(t => `${t.key}=${t.available}`));
    return tabs;
  }, [manualTranscript, autoTranscript, whisperTranscript, translatedTranscripts]);
}

export default function TranscriptTabs({
  transcript,
  manualTranscript,
  autoTranscript,
  whisperTranscript,
  translatedTranscripts,
  selectedLanguage,
  onLanguageChange,
  isTranslating = false,
}: TranscriptTabsProps) {
  const tabs = useTranscriptTabs(manualTranscript, autoTranscript, translatedTranscripts, whisperTranscript);

  const handleSelect = (key: string) => {
    console.log(`[TranscriptTabs] Tab selected: ${key}`);
    onLanguageChange(key);
  };

  // Map selectedLanguage to the active tab key
  const activeTab = tabs.find((t) => t.key === selectedLanguage)?.key ||
    tabs.find((t) => t.available)?.key ||
    selectedLanguage;

  return (
    <LanguageSelector
      tabs={tabs}
      activeTab={activeTab}
      onSelect={handleSelect}
      disabled={isTranslating}
    />
  );
}
