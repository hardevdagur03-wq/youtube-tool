import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useWorkflow } from '../context/WorkflowContext';
import { WorkflowHeader, WorkflowFooter } from '../components/workflow';
import EditorContainer from '../components/editor/EditorContainer';

function getProjectIdFromState(state: any): string | null {
  if (state?.videoId) return state.videoId;
  return null;
}

export default function BlogEditor() {
  const navigate = useNavigate();
  const { state, goToStep } = useWorkflow();
  const [searchParams] = useSearchParams();
  const { videoId } = state;

  const projectId = searchParams.get('project_id') || getProjectIdFromState(state) || videoId;

  const handleContinue = () => {
    goToStep('export');
    navigate('/blog/export');
  };

  const handleBack = () => {
    goToStep('generate');
    navigate('/blog/generate');
  };

  if (!videoId && !projectId) {
    navigate('/blog', { replace: true });
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col h-full"
    >
      <WorkflowHeader currentStep={state.currentStep} />

      <div className="flex-1 min-h-0 mb-4">
        {projectId ? (
          <EditorContainer projectId={projectId} />
        ) : (
          <div className="flex items-center justify-center h-64 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800">
            <p className="text-sm text-gray-400">No project data available. Generate a blog post first.</p>
          </div>
        )}
      </div>

      <WorkflowFooter
        currentStep={state.currentStep}
        onBack={handleBack}
        onContinue={handleContinue}
        continueLabel="Continue to Export →"
      />
    </motion.div>
  );
}
