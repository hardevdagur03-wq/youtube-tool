import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Youtube, Loader2, ArrowRight } from 'lucide-react';
import { Container, Badge, Card } from '../components/ui';
import VideoUrlInput from '../components/blog/VideoUrlInput';
import { useWorkflow } from '../context/WorkflowContext';
import type { VideoMetadataResponse } from '../types';

export default function BlogHome() {
  const navigate = useNavigate();
  const { state, dispatch } = useWorkflow();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleValidUrl = useCallback(async (videoId: string, normalizedUrl: string) => {
    dispatch({ type: 'RESET' });
    dispatch({ type: 'SET_VIDEO', payload: { videoId, normalizedUrl } });
    dispatch({ type: 'SET_STEP_STATUS', payload: { step: 'metadata', status: 'running' } });

    setLoading(true);
    setError(null);

    try {
      const resp = await fetch(`/api/video-metadata/${videoId}`);
      if (!resp.ok) {
        const body = await resp.json().catch(() => null);
        const msg = body?.error || `Server returned ${resp.status} ${resp.statusText}.`;
        setError(msg);
        dispatch({ type: 'SET_STEP_STATUS', payload: { step: 'metadata', status: 'error' } });
        return;
      }
      const data: VideoMetadataResponse = await resp.json();
      dispatch({ type: 'SET_METADATA', payload: data });
      if (data.success) {
        navigate('/blog/metadata');
      } else {
        setError(data.error || 'Failed to load metadata.');
        dispatch({ type: 'SET_STEP_STATUS', payload: { step: 'metadata', status: 'error' } });
      }
    } catch (err) {
      const msg = err instanceof TypeError
        ? 'Could not reach the server. Check your connection.'
        : `Metadata request failed: ${err instanceof Error ? err.message : 'Unknown error'}.`;
      setError(msg);
      dispatch({ type: 'SET_STEP_STATUS', payload: { step: 'metadata', status: 'error' } });
    } finally {
      setLoading(false);
    }
  }, [navigate, dispatch]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-violet-600 via-violet-500 to-violet-700 dark:from-violet-800 dark:via-violet-700 dark:to-violet-900 rounded-b-3xl">
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(255,255,255,0.12),transparent_60%)]" />
          <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-white/5 rounded-full blur-3xl" />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-28 lg:pt-32 pb-16 lg:pb-20">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="max-w-2xl"
          >
            <Badge variant="info">AI Blog Generator</Badge>
            <h1 className="text-[36px] sm:text-[44px] lg:text-[52px] font-extrabold leading-[1.08] tracking-[-0.03em] text-white mt-4 mb-3">
              URL → AI Blog
            </h1>
            <p className="text-[17px] leading-relaxed text-white/75 max-w-lg">
              Convert any YouTube video into a professional AI-generated SEO blog article. Paste a URL and let the AI do the rest.
            </p>
          </motion.div>
        </div>
      </section>

      {/* URL Input */}
      <section className="relative z-10 -mt-6 pb-20">
        <Container>
          <div className="max-w-2xl mx-auto">
            <Card padding="lg">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-violet-50 dark:bg-violet-900/30 flex items-center justify-center flex-shrink-0">
                  <Youtube size={18} className="text-violet-600 dark:text-violet-400" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                    YouTube Video URL
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Enter a YouTube video URL to generate a blog
                  </p>
                </div>
              </div>

              <VideoUrlInput onValidUrl={handleValidUrl} />

              {loading && (
                <div className="mt-6 pt-6 border-t border-gray-100 dark:border-gray-800">
                  <div className="flex items-center gap-2.5 text-sm text-gray-500 dark:text-gray-400">
                    <Loader2 size={14} className="animate-spin text-violet-500" />
                    Fetching video metadata...
                  </div>
                </div>
              )}

              {error && !loading && (
                <div className="mt-6 pt-6 border-t border-gray-100 dark:border-gray-800">
                  <Badge variant="error">{error}</Badge>
                </div>
              )}
            </Card>

            {/* Steps preview */}
            {!loading && !error && (
              <div className="mt-8 text-center">
                <p className="text-xs text-gray-400 dark:text-gray-500 mb-4">WORKFLOW</p>
                <div className="flex items-center justify-center gap-2 text-xs font-medium">
                  {['URL', 'Metadata', 'Transcript', 'Analysis', 'Generate', 'Editor', 'Export'].map((label, i) => (
                    <div key={label} className="flex items-center gap-2">
                      <div className="px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500">
                        {label}
                      </div>
                      {i < 6 && <ArrowRight size={12} className="text-gray-300 dark:text-gray-600" />}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Container>
      </section>
    </motion.div>
  );
}
