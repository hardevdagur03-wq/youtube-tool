import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import TranscriptPipeline from '../components/transcript/TranscriptPipeline';
import type { PipelineStep } from '../types';

describe('TranscriptPipeline', () => {
  it('should render nothing for empty steps', () => {
    const { container } = render(<TranscriptPipeline steps={[]} />);
    expect(container.innerHTML).toBe('');
  });

  it('should show "Not Available" for skipped manual step', () => {
    const steps: PipelineStep[] = [
      {
        name: 'Manual Transcript',
        status: 'skipped',
        detail: 'No manually-created transcript found.',
        duration_seconds: null,
      },
      {
        name: 'Auto Transcript',
        status: 'ok',
        detail: 'auto (en, 100 words)',
        duration_seconds: null,
      },
      {
        name: 'Cleaning Transcript',
        status: 'ok',
        detail: '100 words, 500 chars',
        duration_seconds: null,
      },
      {
        name: 'Ready',
        status: 'ok',
        detail: 'Retrieved in 2.3s from auto',
        duration_seconds: null,
      },
    ];

    render(<TranscriptPipeline steps={steps} />);
    expect(screen.getByText('Manual Transcript')).toBeInTheDocument();
    expect(screen.getByText('Not Available')).toBeInTheDocument();
    expect(screen.getByText('Auto Transcript')).toBeInTheDocument();
    expect(screen.getByText('Cleaning Transcript')).toBeInTheDocument();
    expect(screen.getByText('Ready')).toBeInTheDocument();
  });

  it('should show "Not Available" for errored manual step', () => {
    const steps: PipelineStep[] = [
      {
        name: 'Manual Transcript',
        status: 'error',
        detail: 'No manually created transcript',
        duration_seconds: null,
      },
      {
        name: 'Auto Transcript',
        status: 'ok',
        detail: 'auto (en, 100 words)',
        duration_seconds: null,
      },
      {
        name: 'Ready',
        status: 'ok',
        detail: 'Retrieved in 2.3s from auto',
        duration_seconds: null,
      },
    ];

    render(<TranscriptPipeline steps={steps} />);
    expect(screen.getByText('Not Available')).toBeInTheDocument();
  });

  it('should show checkmark for successful steps', () => {
    const steps: PipelineStep[] = [
      {
        name: 'Manual Transcript',
        status: 'ok',
        detail: 'manual (en, 100 words)',
        duration_seconds: null,
      },
      {
        name: 'Cleaning Transcript',
        status: 'ok',
        detail: '100 words, 500 chars',
        duration_seconds: null,
      },
      {
        name: 'Ready',
        status: 'ok',
        detail: 'Retrieved in 1.2s from manual',
        duration_seconds: null,
      },
    ];

    render(<TranscriptPipeline steps={steps} />);
    expect(screen.getByText('Manual Transcript')).toBeInTheDocument();
    expect(screen.getByText('Cleaning Transcript')).toBeInTheDocument();
    expect(screen.getByText('Ready')).toBeInTheDocument();
  });

  it('should show error step when all stages fail', () => {
    const steps: PipelineStep[] = [
      {
        name: 'Manual Transcript',
        status: 'skipped',
        detail: 'No manual transcript found',
        duration_seconds: null,
      },
      {
        name: 'Auto Transcript',
        status: 'skipped',
        detail: 'No auto transcript found',
        duration_seconds: null,
      },
      {
        name: 'Error',
        status: 'error',
        detail: 'No transcript available from any source.',
        duration_seconds: null,
      },
    ];

    render(<TranscriptPipeline steps={steps} />);
    expect(screen.getByText('Not Available')).toBeInTheDocument();
    expect(screen.getByText('No transcript available from any source.')).toBeInTheDocument();
  });

  it('should display progress count correctly', () => {
    const steps: PipelineStep[] = [
      {
        name: 'Manual Transcript',
        status: 'skipped',
        detail: 'Not available',
        duration_seconds: null,
      },
      {
        name: 'Auto Transcript',
        status: 'ok',
        detail: 'auto (en, 100 words)',
        duration_seconds: null,
      },
      {
        name: 'Cleaning Transcript',
        status: 'ok',
        detail: '100 words',
        duration_seconds: null,
      },
      {
        name: 'Ready',
        status: 'ok',
        detail: 'Retrieved',
        duration_seconds: null,
      },
    ];

    render(<TranscriptPipeline steps={steps} />);
    expect(screen.getByText('4/4 steps')).toBeInTheDocument();
  });
});
