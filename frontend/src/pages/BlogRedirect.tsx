import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWorkflow } from '../context/WorkflowContext';

const stepRoutes: Record<string, string> = {
  url: '/blog',
  metadata: '/blog/metadata',
  transcript: '/blog/transcript',
  analysis: '/blog/analysis',
  generate: '/blog/generate',
  editor: '/blog/editor',
  export: '/blog/export',
};

export default function BlogRedirect() {
  const navigate = useNavigate();
  const { state } = useWorkflow();

  useEffect(() => {
    const target = stepRoutes[state.currentStep] || '/blog';
    navigate(target, { replace: true });
  }, []);

  return null;
}
