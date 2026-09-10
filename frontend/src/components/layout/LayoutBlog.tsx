import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { WorkflowProvider, useWorkflow } from '../../context/WorkflowContext';
import { WorkflowStepper, WorkflowSidebar } from '../workflow';
import { Container } from '../ui';
import type { WorkflowStep } from '../../types';

import Navbar from './Navbar';
import Footer from './Footer';

const pathToStep: Record<string, WorkflowStep> = {
  '/blog': 'url',
  '/blog/metadata': 'metadata',
  '/blog/transcript': 'transcript',
  '/blog/analysis': 'analysis',
  '/blog/generate': 'generate',
  '/blog/editor': 'editor',
  '/blog/export': 'export',
};

function BlogLayoutInner() {
  const location = useLocation();
  const navigate = useNavigate();
  const { state, goToStep } = useWorkflow();

  useEffect(() => {
    const step = pathToStep[location.pathname];
    if (step && step !== state.currentStep) {
      goToStep(step);
    }
  }, [location.pathname]);

  const showSidebar = location.pathname !== '/blog';

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col justify-between">
      <Navbar />
      <div className="pt-16 lg:pt-[68px] flex-1">
        <WorkflowStepper currentStep={state.currentStep} stepStatus={state.stepStatus} />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-20">
          {showSidebar ? (
            <div className="flex gap-8">
              <div className="flex-1 min-w-0">
                <Outlet context={{ state }} />
              </div>
              <aside className="hidden xl:block w-64 flex-shrink-0">
                <WorkflowSidebar currentStep={state.currentStep} stepStatus={state.stepStatus} />
              </aside>
            </div>
          ) : (
            <Outlet context={{ state }} />
          )}
        </div>
      </div>
      <Footer />
    </div>
  );
}

export default function LayoutBlog() {
  return (
    <WorkflowProvider>
      <BlogLayoutInner />
    </WorkflowProvider>
  );
}
