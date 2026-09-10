import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Brain, Sparkles, AlertCircle, RefreshCw } from 'lucide-react';
import { useWorkflow } from '../context/WorkflowContext';
import { WorkflowHeader, WorkflowFooter } from '../components/workflow';
import { Card, Badge } from '../components/ui';
import AnalysisPipeline from '../components/analysis/AnalysisPipeline';
import AnalysisResults from '../components/analysis/AnalysisResults';
import type { ContentAnalysisResult } from '../types';

export default function BlogAnalysis() {
  const navigate = useNavigate();
  const { state, dispatch, goToStep } = useWorkflow();
  const { videoId, processedTranscript, analysis, analysisStatus } = state;
  const [error, setError] = useState<string | null>(null);

  const handleBack = () => {
    goToStep('transcript');
    navigate('/blog/transcript');
  };

  const handleContinue = () => {
    goToStep('generate');
    navigate('/blog/generate');
  };

  const runAnalysis = useCallback(async () => {
    if (!videoId || !processedTranscript?.clean_transcript) return;

    dispatch({ type: 'SET_ANALYSIS_STATUS', payload: 'analyzing' });
    setError(null);

    try {
      const body = {
        video_id: videoId,
        transcript: processedTranscript.clean_transcript,
        language_info: processedTranscript.language || undefined,
        metadata: state.metadata ? {
          video: state.metadata,
          success: true,
          error: null,
        } : undefined,
      };

      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail?.error || errData?.error || `Analysis request failed (${res.status})`);
      }

      const data = await res.json();
      const result = data as ContentAnalysisResult;

      if (!result.success) {
        throw new Error(result.error || 'Analysis returned unsuccessful');
      }

      dispatch({ type: 'SET_ANALYSIS', payload: { result, status: 'ok' } });
    } catch (err: any) {
      setError(err.message || 'Analysis failed');
      dispatch({ type: 'SET_ANALYSIS_STATUS', payload: 'error' });
    }
  }, [videoId, processedTranscript, state.metadata, dispatch]);

  useEffect(() => {
    if (!videoId) {
      navigate('/blog', { replace: true });
      return;
    }

    if (!processedTranscript?.clean_transcript) {
      goToStep('transcript');
      navigate('/blog/transcript');
      return;
    }

    if (analysisStatus === 'idle' && !analysis) {
      runAnalysis();
    }
  }, [videoId, processedTranscript, analysisStatus, analysis, navigate, goToStep, runAnalysis]);

  if (!videoId) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <WorkflowHeader currentStep={state.currentStep} />

      {/* Pipeline Status */}
      {analysisStatus !== 'ok' && (
        <Card padding="lg" className="mb-6">
          <AnalysisPipeline
            status={analysisStatus}
            processingTimeMs={analysis?.analysis_time_ms}
            provider={analysis?.llm_provider}
            model={analysis?.llm_model}
          />

          {analysisStatus === 'analyzing' && (
            <div className="flex items-center justify-center gap-2 mt-4 text-sm text-indigo-600 dark:text-indigo-400">
              <Sparkles size={14} className="animate-pulse" />
              Analyzing transcript content...
            </div>
          )}

          {error && (
            <div className="mt-4 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <div className="flex items-start gap-3">
                <AlertCircle size={18} className="text-red-500 mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-red-800 dark:text-red-200">Analysis Failed</p>
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1">{error}</p>
                  <button
                    onClick={runAnalysis}
                    className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 text-xs font-medium hover:bg-red-200 dark:hover:bg-red-900/60 transition-colors"
                  >
                    <RefreshCw size={12} />
                    Retry Analysis
                  </button>
                </div>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Analysis Results */}
      {analysis && analysisStatus === 'ok' && (
        <>
          <div className="mb-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center shadow-lg shadow-indigo-200 dark:shadow-indigo-900/30">
              <Brain size={20} className="text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">Content Analysis Complete</h2>
              <p className="text-xs text-gray-500">
                {analysis.llm_provider}/{analysis.llm_model} · {analysis.analysis_time_ms.toFixed(0)}ms · v{analysis.prompt_version}
              </p>
            </div>
          </div>

          <AnalysisResults analysis={analysis} />

          {analysis.keywords.primary && (
            <div className="mt-6 flex flex-wrap items-center gap-2 text-xs text-gray-400">
              <span className="font-medium">Primary Keyword:</span>
              <Badge variant="info">{analysis.keywords.primary}</Badge>
            </div>
          )}
        </>
      )}

      <WorkflowFooter
        currentStep={state.currentStep}
        onBack={handleBack}
        onContinue={handleContinue}
        continueLabel="Proceed to Blog Generation →"
        disableContinue={analysisStatus !== 'ok'}
      />
    </motion.div>
  );
}
