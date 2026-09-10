import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { PenLine, Sparkles, Loader2 } from 'lucide-react';
import { useWorkflow } from '../context/WorkflowContext';
import { WorkflowHeader, WorkflowFooter } from '../components/workflow';
import { Card, Badge } from '../components/ui';

export default function BlogGenerate() {
  const navigate = useNavigate();
  const { state, dispatch, goToStep } = useWorkflow();
  const { videoId, transcript, analysis } = state;
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    if (!videoId) return;
    setGenerating(true);
    setError(null);
    dispatch({ type: 'SET_STEP_STATUS', payload: { step: 'generate', status: 'running' } });

    try {
      const resp = await fetch(`/api/blog/${videoId}`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => null);
        throw new Error(body?.detail?.error || body?.error || `Server returned ${resp.status}`);
      }
      const data = await resp.json();
      if (data.success) {
        dispatch({ type: 'SET_STEP_STATUS', payload: { step: 'generate', status: 'ok' } });
        goToStep('editor');
        navigate('/blog/editor');
      } else {
        throw new Error(data.error || 'Blog generation failed');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Blog generation failed';
      setError(msg);
      dispatch({ type: 'SET_STEP_STATUS', payload: { step: 'generate', status: 'error' } });
    } finally {
      setGenerating(false);
    }
  }, [videoId, navigate, dispatch, goToStep]);

  const handleContinue = () => {
    goToStep('editor');
    navigate('/blog/editor');
  };

  const handleBack = () => {
    goToStep('analysis');
    navigate('/blog/analysis');
  };

  if (!videoId) {
    navigate('/blog', { replace: true });
    return null;
  }

  const hasContent = transcript?.success && analysis?.success;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <WorkflowHeader currentStep={state.currentStep} />

      <Card padding="lg" className="mb-6">
        <div className="flex flex-col items-center text-center py-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center mb-6 shadow-lg shadow-emerald-200 dark:shadow-emerald-900/30">
            <PenLine size={32} className="text-white" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
            Generate AI Blog
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mb-4">
            Generate a fully formatted, SEO-optimized blog article from the transcript and AI analysis.
          </p>
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 text-sm font-medium mb-6">
            <Sparkles size={15} />
            AI-powered blog generation
          </div>

          {!hasContent && (
            <Badge variant="warning">Missing transcript or analysis data — blog may be incomplete</Badge>
          )}

          {error && (
            <div className="mt-4">
              <Badge variant="error">{error}</Badge>
            </div>
          )}

          {!generating && !error && (
            <button
              onClick={handleGenerate}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold bg-gradient-to-r from-emerald-600 to-emerald-500 text-white shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all-200"
            >
              <Sparkles size={16} />
              Generate Blog Article
            </button>
          )}

          {generating && (
            <div className="flex items-center gap-2.5 text-sm text-gray-500 dark:text-gray-400">
              <Loader2 size={16} className="animate-spin text-emerald-500" />
              Generating blog article...
            </div>
          )}
        </div>
      </Card>

      <WorkflowFooter
        currentStep={state.currentStep}
        onBack={handleBack}
        onContinue={handleContinue}
        continueLabel="Skip to Editor →"
      />
    </motion.div>
  );
}