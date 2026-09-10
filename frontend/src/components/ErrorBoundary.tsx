import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex items-center justify-center min-h-[200px]">
          <div className="text-center p-8">
            <div className="w-12 h-12 rounded-full bg-red-50 dark:bg-red-900/30 flex items-center justify-center mx-auto mb-4">
              <span className="text-red-500 text-xl">!</span>
            </div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
              Something went wrong
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Please refresh the page to try again.
            </p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}