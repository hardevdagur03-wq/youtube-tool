import { motion } from 'framer-motion';
import { Badge } from '../ui';
import type { WorkflowStep } from '../../types';

const stepTitles: Record<WorkflowStep, { title: string; subtitle: string }> = {
  url: { title: 'Video URL', subtitle: 'Enter a YouTube video URL to get started' },
  metadata: { title: 'Video Metadata', subtitle: 'Review video details before processing' },
  transcript: { title: 'Transcript Extraction', subtitle: 'Retrieving the best available transcript' },
  analysis: { title: 'AI Analysis', subtitle: 'Analyzing video content and transcript' },
  generate: { title: 'Blog Generation', subtitle: 'Generating SEO-optimized blog content' },
  editor: { title: 'Blog Editor', subtitle: 'Review and refine your generated blog' },
  export: { title: 'Export', subtitle: 'Download your blog in multiple formats' },
};

const stepNumbers: Record<WorkflowStep, number> = {
  url: 1,
  metadata: 2,
  transcript: 3,
  analysis: 4,
  generate: 5,
  editor: 6,
  export: 7,
};

interface WorkflowHeaderProps {
  currentStep: WorkflowStep;
}

export default function WorkflowHeader({ currentStep }: WorkflowHeaderProps) {
  const info = stepTitles[currentStep];
  const stepNum = stepNumbers[currentStep];

  return (
    <motion.div
      key={currentStep}
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="mb-6"
    >
      <div className="flex items-center gap-3 mb-2">
        <Badge variant="info">Step {stepNum} of 7</Badge>
        <span className="text-xs text-gray-400 dark:text-gray-500 font-medium">
          AI Blog Workflow
        </span>
      </div>
      <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
        {info.title}
      </h1>
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {info.subtitle}
      </p>
    </motion.div>
  );
}
