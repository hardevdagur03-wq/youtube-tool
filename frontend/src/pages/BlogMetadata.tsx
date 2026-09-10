import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useWorkflow } from '../context/WorkflowContext';
import { WorkflowHeader, WorkflowFooter, WorkflowCompletionCard, WorkflowSkeleton } from '../components/workflow';
import VideoDetails from '../components/blog/VideoDetails';

export default function BlogMetadata() {
  const navigate = useNavigate();
  const { state, goToStep } = useWorkflow();
  const { metadataResponse, metadata, videoId, stepStatus } = state;
  const isOk = stepStatus.metadata === 'ok';
  const isError = stepStatus.metadata === 'error';

  const handleContinue = () => {
    goToStep('transcript');
    navigate('/blog/transcript');
  };

  const handleBack = () => {
    goToStep('url');
    navigate('/blog');
  };

  if (!videoId) {
    navigate('/blog', { replace: true });
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <WorkflowHeader currentStep={state.currentStep} />

      {isError && (
        <div className="mb-6 p-6 rounded-2xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
          <p className="text-sm text-red-600 dark:text-red-400">
            {state.error || 'Failed to load metadata.'}
            <button
              onClick={handleBack}
              className="ml-2 underline hover:no-underline"
            >
              Try again
            </button>
          </p>
        </div>
      )}

      {!isOk && !isError && (
        <WorkflowSkeleton />
      )}

      {isOk && metadata && (
        <>
          <VideoDetails metadata={metadata} />

          <div className="mt-8">
            <WorkflowCompletionCard
              title="Metadata Retrieved Successfully"
              subtitle="The video has been analyzed successfully."
              nextStepLabel="Continue to Transcript"
              nextStepDescription="Extract the transcript required for AI Blog Generation. The engine will automatically try manual captions, auto captions, or Whisper speech-to-text."
              estimatedTime="10-30 seconds"
              status="ok"
              onContinue={handleContinue}
            />
          </div>
        </>
      )}

      <WorkflowFooter
        currentStep={state.currentStep}
        onBack={handleBack}
        onContinue={isOk ? handleContinue : undefined}
        disableContinue={!isOk}
        continueLabel="Continue to Transcript →"
      />
    </motion.div>
  );
}
