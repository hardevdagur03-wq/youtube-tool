import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown,
  ChevronUp,
  Clock,
  MessageSquareText,
  Loader2,
} from 'lucide-react';
import { Card, Badge } from '../ui';
import type { TranscriptResult } from '../../types';
import { getLanguageLabel } from '../../types';
import TranscriptSearch from './TranscriptSearch';
import TranscriptActions from './TranscriptActions';
import TranscriptTabs from './TranscriptTabs';

const sourceVariants = {
  manual: { label: 'Manual', variant: 'success' as const },
  auto: { label: 'Auto-Generated', variant: 'info' as const },
  whisper: { label: 'Whisper STT', variant: 'warning' as const },
} as const;

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

interface TranscriptViewerProps {
  transcript: TranscriptResult;
  manualTranscript: TranscriptResult | null;
  autoTranscript: TranscriptResult | null;
  whisperTranscript?: TranscriptResult | null;
  translatedTranscripts?: Record<string, TranscriptResult>;
  selectedLanguage?: string;
  onLanguageChange?: (language: string) => Promise<void>;
  isTranslating?: boolean;
}

export default function TranscriptViewer({
  transcript,
  manualTranscript,
  autoTranscript,
  whisperTranscript = null,
  translatedTranscripts = {},
  selectedLanguage: externalSelectedLang,
  onLanguageChange,
  isTranslating = false,
}: TranscriptViewerProps) {
  const [expanded, setExpanded] = useState(true);
  const [showTimestamps, setShowTimestamps] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Determine which transcript to display based on selectedLanguage
  const visibleTranscript = useMemo<TranscriptResult>(() => {
    const lang = externalSelectedLang || transcript.language;
    console.log(`[TranscriptViewer] visibleTranscript: lang=${lang}`);

    // If selected language matches manual, show manual
    if (manualTranscript && lang === manualTranscript.language) {
      console.log(`[TranscriptViewer] -> using MANUAL`);
      return manualTranscript;
    }

    // If selected language matches auto, show auto
    if (autoTranscript && lang === autoTranscript.language) {
      console.log(`[TranscriptViewer] -> using AUTO`);
      return autoTranscript;
    }

    // If selected language matches Whisper, show Whisper
    if (whisperTranscript && lang === whisperTranscript.language) {
      console.log(`[TranscriptViewer] -> using WHISPER`);
      return whisperTranscript;
    }

    // If translated version exists, show it
    if (translatedTranscripts[lang]) {
      console.log(`[TranscriptViewer] -> using TRANSLATED`);
      return translatedTranscripts[lang];
    }

    // Fallback
    console.log(`[TranscriptViewer] -> FALLBACK to original`);
    return transcript;
  }, [transcript, manualTranscript, autoTranscript, whisperTranscript, translatedTranscripts, externalSelectedLang]);

  const activeSource = visibleTranscript.source || transcript.source;
  const source = sourceVariants[activeSource] || sourceVariants.manual;
  const isTranslated = externalSelectedLang && externalSelectedLang !== transcript.language;
  const hasSegments = visibleTranscript.segments.length > 0;

  const filteredSegments = searchQuery
    ? visibleTranscript.segments.filter((s) =>
        s.text.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : visibleTranscript.segments;

  const sourceLabel = isTranslated
    ? `${source.label} (Translated to ${getLanguageLabel(externalSelectedLang!)})`
    : source.label;

  return (
    <Card padding="lg" className="mb-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-violet-50 dark:bg-violet-900/30 flex items-center justify-center flex-shrink-0">
            <MessageSquareText
              size={18}
              className="text-violet-600 dark:text-violet-400"
            />
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-white">
              Transcript
            </h3>
            <div className="flex flex-wrap items-center gap-2 mt-1">
              <Badge variant={source.variant}>{sourceLabel}</Badge>
              {isTranslated && (
                <Badge variant="warning">
                  Translated to {getLanguageLabel(externalSelectedLang!)}
                </Badge>
              )}
              <span className="text-xs text-gray-400 dark:text-gray-500">
                {visibleTranscript.word_count.toLocaleString()} words ·{' '}
                {visibleTranscript.estimated_read_time}
              </span>
            </div>
          </div>
        </div>

        <TranscriptActions
          transcript={visibleTranscript}
          allTranscripts={{
            [transcript.language]: transcript,
            ...(manualTranscript ? { manual: manualTranscript } : {}),
            ...(autoTranscript ? { auto: autoTranscript } : {}),
            ...(whisperTranscript ? { whisper: whisperTranscript } : {}),
            ...translatedTranscripts,
          }}
        />
      </div>

      {/* Language Tabs */}
      <div className="mb-4">
        <TranscriptTabs
          transcript={transcript}
          manualTranscript={manualTranscript}
          autoTranscript={autoTranscript}
          whisperTranscript={whisperTranscript}
          translatedTranscripts={translatedTranscripts}
          selectedLanguage={externalSelectedLang || transcript.language}
          onLanguageChange={async (lang) => {
            console.log(`[TranscriptViewer] onLanguageChange: ${lang}`);
            if (onLanguageChange) {
              await onLanguageChange(lang);
            }
          }}
          isTranslating={isTranslating}
        />
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        {[
          {
            label: 'Segments',
            value: visibleTranscript.segments.length.toLocaleString(),
          },
          {
            label: 'Words',
            value: visibleTranscript.word_count.toLocaleString(),
          },
          {
            label: 'Characters',
            value: visibleTranscript.character_count.toLocaleString(),
          },
          {
            label: 'Read Time',
            value: visibleTranscript.estimated_read_time,
          },
        ].map((stat) => (
          <div
            key={stat.label}
            className="px-4 py-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800"
          >
            <div className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">
              {stat.label}
            </div>
            <div className="text-sm font-semibold text-gray-900 dark:text-white">
              {stat.value}
            </div>
          </div>
        ))}
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <TranscriptSearch onSearch={setSearchQuery} />

        <button
          onClick={() => setShowTimestamps(!showTimestamps)}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all-200 ${
            showTimestamps
              ? 'bg-violet-50 dark:bg-violet-900/20 border-violet-200 dark:border-violet-800 text-violet-700 dark:text-violet-300'
              : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400'
          }`}
        >
          <Clock size={12} />
          Timestamps
        </button>

        <button
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all-200"
        >
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {expanded ? 'Collapse' : 'Expand'}
        </button>

        {isTranslating && (
          <span className="inline-flex items-center gap-1.5 text-xs text-violet-500 dark:text-violet-400">
            <Loader2 size={12} className="animate-spin" />
            Translating...
          </span>
        )}
      </div>

      {/* Segments */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="border border-gray-100 dark:border-gray-800 rounded-xl overflow-hidden"
          >
            {hasSegments ? (
              <div className="divide-y divide-gray-50 dark:divide-gray-800/50 max-h-[500px] overflow-y-auto">
                {filteredSegments.length === 0 && searchQuery ? (
                  <div className="p-8 text-center text-sm text-gray-400 dark:text-gray-500">
                    No segments match "{searchQuery}"
                  </div>
                ) : (
                  filteredSegments.map((seg, i) => (
                    <div
                      key={i}
                      className="flex gap-3 px-5 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors"
                    >
                      {showTimestamps && (
                        <span className="flex-shrink-0 w-14 text-xs font-mono text-gray-400 dark:text-gray-500 pt-0.5 select-none">
                          {formatTime(seg.start)}
                        </span>
                      )}
                      <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                        {seg.text}
                      </p>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div className="p-8 text-center text-sm text-gray-400 dark:text-gray-500">
                {visibleTranscript.paragraph_text ? (
                  <p className="text-left whitespace-pre-line leading-relaxed">
                    {visibleTranscript.paragraph_text}
                  </p>
                ) : (
                  'No transcript segments available.'
                )}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
