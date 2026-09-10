import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useWorkflow } from '../context/WorkflowContext';
import {
  WorkflowHeader,
  WorkflowFooter,
  WorkflowCompletionCard,
  WorkflowSkeleton,
} from '../components/workflow';
import TranscriptPipeline from '../components/transcript/TranscriptPipeline';
import ProcessingPipelineSteps from '../components/transcript/ProcessingPipelineSteps';
import TranscriptViewer from '../components/transcript/TranscriptViewer';
import TranscriptError from '../components/transcript/TranscriptError';
import type { TranscriptResult, ProcessingResult } from '../types';
import { transcriptService } from '../services/TranscriptService';

export default function BlogTranscript() {
  const navigate = useNavigate();
  const { state, dispatch, goToStep } = useWorkflow();
  const {
    videoId,
    stepStatus,
    processedTranscript,
    processingStatus,
    metadata,
  } = state;
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isTranslating, setIsTranslating] = useState(false);

  // Separate transcript stores
  const [transcript, setTranscript] = useState<TranscriptResult | null>(null);
  const [manualTranscript, setManualTranscript] =
    useState<TranscriptResult | null>(null);
  const [autoTranscript, setAutoTranscript] =
    useState<TranscriptResult | null>(null);
  const [whisperTranscript, setWhisperTranscript] =
    useState<TranscriptResult | null>(null);
  const [translatedTranscripts, setTranslatedTranscripts] = useState<
    Record<string, TranscriptResult>
  >({});
  const [pipelineSteps, setPipelineSteps] = useState<any[]>([]);
  const [availableLanguages, setAvailableLanguages] = useState<any[]>([]);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('en');

  const isTranscriptOk = stepStatus.transcript === 'ok';
  const isProcessingDone = processingStatus === 'ok';
  const showProcessing =
    transcript?.success && !isProcessingDone && processingStatus !== 'error';

  useEffect(() => {
    if (!videoId) {
      navigate('/blog', { replace: true });
      return;
    }
    if (stepStatus.transcript === 'pending') {
      fetchAllTranscripts();
    }
  }, [videoId]);

  useEffect(() => {
    if (
      transcript?.success &&
      processingStatus === 'idle' &&
      !processedTranscript
    ) {
      processTranscript();
    }
  }, [transcript]);

  const fetchAllTranscripts = async () => {
    dispatch({
      type: 'SET_STEP_STATUS',
      payload: { step: 'transcript', status: 'running' },
    });
    setLoading(true);
    setError(null);

    try {
      const data = await transcriptService.fetchAllTranscripts(videoId!);
      console.log(`[BlogTranscript] All transcripts response:`, data);

      if (!data.success) {
        const details = (data.pipeline_steps || [])
          .filter((step) => step.detail)
          .map((step) => `${step.name}: ${step.detail}`)
          .join(' ');
        setError(details || 'Failed to load any transcript.');
        setPipelineSteps(data.pipeline_steps || []);
        dispatch({
          type: 'SET_STEP_STATUS',
          payload: { step: 'transcript', status: 'error' },
        });
        return;
      }

      const firstAvailable = data.auto || data.manual || data.whisper;
      setManualTranscript(data.manual || null);
      setAutoTranscript(data.auto || null);
      setWhisperTranscript(data.whisper || null);
      setTranscript(firstAvailable);
      setPipelineSteps(data.pipeline_steps || []);
      setAvailableLanguages(data.available_languages || []);

      if (firstAvailable) {
        setSelectedLanguage(firstAvailable.language);
        dispatch({ type: 'SET_TRANSCRIPT', payload: firstAvailable });
      }
    } catch (err) {
      const msg =
        err instanceof TypeError
          ? 'Could not reach the server. Check your connection.'
          : `Transcript request failed: ${
              err instanceof Error ? err.message : 'Unknown error'
            }.`;
      setError(msg);
      dispatch({
        type: 'SET_STEP_STATUS',
        payload: { step: 'transcript', status: 'error' },
      });
    } finally {
      setLoading(false);
    }
  };

  const translateTranscript = useCallback(
    async (targetLang: string) => {
      if (!videoId) return;
      const source = autoTranscript || manualTranscript || whisperTranscript || transcript;
      if (!source) return;

      console.log(
        `[BlogTranscript] translate: targetLang=${targetLang}, source.lang=${source.language}`,
      );

      if (targetLang === source.language) {
        setSelectedLanguage(targetLang);
        return;
      }

      if (translatedTranscripts[targetLang]) {
        setSelectedLanguage(targetLang);
        return;
      }

      const cached = transcriptService.getCachedTranslation(
        videoId,
        targetLang,
      );
      if (cached) {
        setTranslatedTranscripts((prev) => ({
          ...prev,
          [targetLang]: cached,
        }));
        setSelectedLanguage(targetLang);
        return;
      }

      setIsTranslating(true);
      try {
        const data = await transcriptService.translateTranscript(
          videoId,
          targetLang,
        );
        console.log(`[BlogTranscript] Translation API response:`, data);
        if (data.success && data.language !== source.language) {
          setTranslatedTranscripts((prev) => ({
            ...prev,
            [targetLang]: data,
          }));
        }
        setSelectedLanguage(targetLang);
      } catch (err) {
        console.error(`[BlogTranscript] Translation failed:`, err);
      } finally {
        setIsTranslating(false);
      }
    },
    [videoId, transcript, autoTranscript, manualTranscript, whisperTranscript, translatedTranscripts],
  );

  const handleLanguageChange = async (lang: string) => {
    console.log(`[BlogTranscript] Language change: ${lang}`);
    setSelectedLanguage(lang);
    const source = autoTranscript || manualTranscript || whisperTranscript || transcript;
    if (source && lang !== source.language && !translatedTranscripts[lang]) {
      await translateTranscript(lang);
    }
  };

  const processTranscript = async () => {
    if (!videoId) return;
    dispatch({ type: 'SET_PROCESSING_STATUS', payload: 'processing' });
    setProcessing(true);

    try {
      const resp = await fetch(
        `/api/transcript/${videoId}/process?remove_fillers=false`,
        { method: 'POST' },
      );
      if (!resp.ok) {
        const body = await resp.json().catch(() => null);
        setError(
          body?.error ||
            `Server returned ${resp.status} ${resp.statusText}.`,
        );
        dispatch({ type: 'SET_PROCESSING_STATUS', payload: 'error' });
        return;
      }
      const data: ProcessingResult = await resp.json();
      dispatch({
        type: 'SET_PROCESSED_TRANSCRIPT',
        payload: { result: data, status: data.success ? 'ok' : 'error' },
      });
      if (!data.success) {
        setError(data.error || 'Failed to process transcript.');
      }
    } catch (err) {
      setError(
        err instanceof TypeError
          ? 'Could not reach the server. Check your connection.'
          : `Processing request failed: ${
              err instanceof Error ? err.message : 'Unknown error'
            }.`,
      );
      dispatch({ type: 'SET_PROCESSING_STATUS', payload: 'error' });
    } finally {
      setProcessing(false);
    }
  };

  const handleContinue = () => {
    goToStep('analysis');
    navigate('/blog/analysis');
  };

  const handleBack = () => {
    goToStep('metadata');
    navigate('/blog/metadata');
  };

  const handleRetry = () => {
    if (videoId) {
      transcriptService.clearCache();
      fetchAllTranscripts();
    }
  };

  const handleReProcess = () => {
    if (videoId) processTranscript();
  };

  if (!videoId) return null;

  const steps =
    processedTranscript?.processing_steps || pipelineSteps;
  const displayText =
    processedTranscript?.clean_transcript ||
    transcript?.paragraph_text ||
    transcript?.plain_text;

  const buildViewerTranscript = (): TranscriptResult | null => {
    return transcript
      ? { ...transcript, pipeline_steps: pipelineSteps, available_languages: availableLanguages }
      : null;
  };

  console.log(
    `[BlogTranscript] RENDER: selectedLanguage=${selectedLanguage}, manual=${manualTranscript ? 'YES' : 'NULL'}, auto=${autoTranscript ? 'YES' : 'NULL'}, whisper=${whisperTranscript ? 'YES' : 'NULL'}, translated=${Object.keys(translatedTranscripts).join(',') || 'none'}`,
  );

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <WorkflowHeader currentStep={state.currentStep} />

      {metadata && (
        <div className="mb-6 p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                {metadata.title || 'Untitled'}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {metadata.channel.name} ·{' '}
                {metadata.duration.readable || metadata.duration.compact}
              </p>
            </div>
          </div>
        </div>
      )}

      {loading && !transcript && <WorkflowSkeleton />}

      {steps && steps.length > 0 && (
        <div className="mb-6">
          <TranscriptPipeline steps={steps as any} />
        </div>
      )}

      {showProcessing && (
        <div className="mb-6">
          <ProcessingPipelineSteps
            transcript={transcript!}
            isProcessing={processing}
            processingResult={processedTranscript}
          />
        </div>
      )}

      {error && !loading && !processing && (
        <TranscriptError message={error} onRetry={handleRetry} />
      )}

      {isTranscriptOk && transcript && !showProcessing && (
        <div className="mb-6">
          <TranscriptViewer
            transcript={buildViewerTranscript()!}
            manualTranscript={manualTranscript}
            autoTranscript={autoTranscript}
            whisperTranscript={whisperTranscript}
            translatedTranscripts={translatedTranscripts}
            selectedLanguage={selectedLanguage}
            onLanguageChange={handleLanguageChange}
            isTranslating={isTranslating}
          />
        </div>
      )}

      {isProcessingDone && processedTranscript && (
        <>
          <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard
              label="Words"
              value={processedTranscript.statistics.word_count.toLocaleString()}
            />
            <StatCard
              label="Sentences"
              value={processedTranscript.statistics.sentence_count.toLocaleString()}
            />
            <StatCard
              label="Read Time"
              value={processedTranscript.statistics.estimated_read_time}
            />
            <StatCard
              label="Language"
              value={
                selectedLanguage === 'en'
                  ? 'EN'
                  : selectedLanguage.toUpperCase()
              }
              sub={
                selectedLanguage !== transcript?.language
                  ? `translated from ${transcript?.language?.toUpperCase()}`
                  : undefined
              }
            />
          </div>

          <div className="mb-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              AI-Ready Transcript
            </h3>
            <div className="prose prose-sm dark:prose-invert max-w-none text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
              {displayText ? (
                displayText.length > 2000
                  ? displayText.slice(0, 2000) + '...'
                  : displayText
              ) : (
                <span className="italic text-gray-400">
                  No text available
                </span>
              )}
            </div>
          </div>

          {processedTranscript.paragraphs.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Paragraphs ({processedTranscript.paragraphs.length})
              </h3>
              <div className="space-y-2">
                {processedTranscript.paragraphs.slice(0, 5).map((p, i) => (
                  <p
                    key={i}
                    className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed border-l-2 border-violet-300 dark:border-violet-700 pl-3"
                  >
                    {p.length > 200 ? p.slice(0, 200) + '...' : p}
                  </p>
                ))}
                {processedTranscript.paragraphs.length > 5 && (
                  <p className="text-xs text-gray-400 italic">
                    + {processedTranscript.paragraphs.length - 5} more
                    paragraphs
                  </p>
                )}
              </div>
            </div>
          )}

          <div className="mt-8">
            <WorkflowCompletionCard
              title="Transcript Processed Successfully"
              subtitle={`${processedTranscript.statistics.word_count.toLocaleString()} words · ${processedTranscript.statistics.estimated_read_time} · ${processedTranscript.processing_time_ms.toFixed(0)}ms processing`}
              nextStepLabel="Continue to AI Analysis"
              nextStepDescription="Analyze the cleaned transcript with AI to extract topics, sentiment, and insights for blog generation."
              estimatedTime="15-30 seconds"
              status="ok"
              onContinue={handleContinue}
            />
          </div>
        </>
      )}

      {isTranscriptOk && !isProcessingDone && !processing && processingStatus === 'idle' && (
        <div className="mt-8">
          <WorkflowCompletionCard
            title="Transcript Retrieved"
            subtitle="Processing the transcript for AI readiness..."
            nextStepLabel="Process Transcript"
            nextStepDescription="Clean, normalize, and structure the transcript for AI consumption."
            estimatedTime="2-5 seconds"
            status="running"
            onContinue={handleReProcess}
          />
        </div>
      )}

      <WorkflowFooter
        currentStep={state.currentStep}
        onBack={handleBack}
        onContinue={isProcessingDone ? handleContinue : undefined}
        disableContinue={!isProcessingDone}
        continueLabel={isProcessingDone ? 'Continue to Analysis →' : undefined}
      />
    </motion.div>
  );
}

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800">
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-lg font-bold text-gray-900 dark:text-white">{value}</p>
      {sub && (
        <p className="text-[10px] text-violet-500 dark:text-violet-400">
          {sub}
        </p>
      )}
    </div>
  );
}
