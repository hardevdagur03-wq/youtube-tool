import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import { ThemeProvider } from './theme/ThemeContext';
import { WorkflowProvider } from './context/WorkflowContext';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/layout/Layout';
import LayoutBlog from './components/layout/LayoutBlog';
import Home from './pages/Home';

const Metadata = lazy(() => import('./pages/Metadata'));
const Blog = lazy(() => import('./pages/Blog'));
const BlogHome = lazy(() => import('./pages/BlogHome'));
const BlogMetadata = lazy(() => import('./pages/BlogMetadata'));
const BlogTranscript = lazy(() => import('./pages/BlogTranscript'));
const BlogAnalysis = lazy(() => import('./pages/BlogAnalysis'));
const BlogGenerate = lazy(() => import('./pages/BlogGenerate'));
const BlogEditor = lazy(() => import('./pages/BlogEditor'));
const BlogExport = lazy(() => import('./pages/BlogExport'));
const Transcript = lazy(() => import('./pages/Transcript'));
const Docs = lazy(() => import('./pages/Docs'));

function SuspenseWrapper({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[200px]">
        <div className="animate-pulse text-sm text-gray-400">Loading...</div>
      </div>
    }>
      {children}
    </Suspense>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <ErrorBoundary>
          <Routes>
            <Route element={<LayoutBlog />}>
              <Route path="/blog/url" element={
                <WorkflowProvider><SuspenseWrapper><BlogHome /></SuspenseWrapper></WorkflowProvider>
              } />
              <Route path="/blog/metadata" element={
                <WorkflowProvider><SuspenseWrapper><BlogMetadata /></SuspenseWrapper></WorkflowProvider>
              } />
              <Route path="/blog/transcript" element={
                <WorkflowProvider><SuspenseWrapper><BlogTranscript /></SuspenseWrapper></WorkflowProvider>
              } />
              <Route path="/blog/analysis" element={
                <WorkflowProvider><SuspenseWrapper><BlogAnalysis /></SuspenseWrapper></WorkflowProvider>
              } />
              <Route path="/blog/generate" element={
                <WorkflowProvider><SuspenseWrapper><BlogGenerate /></SuspenseWrapper></WorkflowProvider>
              } />
              <Route path="/blog/editor" element={
                <WorkflowProvider><SuspenseWrapper><BlogEditor /></SuspenseWrapper></WorkflowProvider>
              } />
              <Route path="/blog/export" element={
                <WorkflowProvider><SuspenseWrapper><BlogExport /></SuspenseWrapper></WorkflowProvider>
              } />
              <Route path="/blog" element={
                <WorkflowProvider><SuspenseWrapper><BlogHome /></SuspenseWrapper></WorkflowProvider>
              } />
            </Route>
            <Route element={<Layout />}>
              <Route path="/" element={<Home />} />
              <Route path="/metadata" element={<SuspenseWrapper><Metadata /></SuspenseWrapper>} />
              <Route path="/transcript" element={<SuspenseWrapper><Transcript /></SuspenseWrapper>} />
              <Route path="/docs" element={<SuspenseWrapper><Docs /></SuspenseWrapper>} />
              <Route path="/blog-legacy" element={<SuspenseWrapper><Blog /></SuspenseWrapper>} />
            </Route>
          </Routes>
        </ErrorBoundary>
      </ThemeProvider>
    </BrowserRouter>
  );
}
