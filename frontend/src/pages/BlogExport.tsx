import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Download,
  FileText,
  FileCode,
  FileType,
  File,
  CheckCircle2,
  Loader2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Package,
  RotateCcw,
  ExternalLink,
  AlertTriangle,
} from 'lucide-react';
import { useWorkflow } from '../context/WorkflowContext';
import { WorkflowHeader, WorkflowFooter } from '../components/workflow';
import { Card, Badge } from '../components/ui';

interface ExportFormat {
  id: string;
  label: string;
  icon: typeof FileText;
  mime: string;
  ext: string;
  description: string;
}

const FORMATS: ExportFormat[] = [
  { id: 'markdown', label: 'Markdown', icon: FileText, mime: 'text/markdown', ext: '.md', description: 'GitHub-compatible Markdown for blogs, docs, and dev platforms' },
  { id: 'html', label: 'HTML', icon: FileCode, mime: 'text/html', ext: '.html', description: 'Semantic HTML5 with SEO meta, Open Graph, and Schema markup' },
  { id: 'docx', label: 'DOCX', icon: FileType, mime: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', ext: '.docx', description: 'Microsoft Word document with professional formatting' },
  { id: 'pdf', label: 'PDF', icon: File, mime: 'application/pdf', ext: '.pdf', description: 'Publication-quality PDF with typography and clickable TOC' },
];

interface ExportFileResult {
  format: string;
  filename: string;
  size_display: string;
  download_url: string;
  mime_type: string;
  valid: boolean;
}

export default function BlogExport() {
  const navigate = useNavigate();
  const { state, reset } = useWorkflow();
  const { videoId, processedTranscript, transcript, metadata, analysis } = state;

  const [selectedFormats, setSelectedFormats] = useState<Set<string>>(
    new Set(['markdown', 'html', 'docx', 'pdf'])
  );
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState<{
    success: boolean;
    files: ExportFileResult[];
    zip_download?: string;
    error?: string;
  } | null>(null);
  const [expanded, setExpanded] = useState(true);

  const toggleFormat = (id: string) => {
    setSelectedFormats((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        if (next.size > 1) next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleExport = useCallback(async () => {
    if (selectedFormats.size === 0) return;
    setExporting(true);
    setExportResult(null);

    const content = processedTranscript?.clean_transcript ||
      transcript?.paragraph_text ||
      transcript?.plain_text || '';

    const requestBody = {
      blog_title: metadata?.title || 'Blog Article',
      slug: (metadata?.title || 'blog-article').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''),
      meta_title: metadata?.title || '',
      meta_description: analysis?.summary?.short || '',
      author: metadata?.channel?.name || '',
      publish_date: metadata?.published_at?.iso?.split('T')[0] || new Date().toISOString().split('T')[0],
      category: analysis?.category || metadata?.category_id || 'Technology',
      tags: metadata?.tags || [],
      primary_keyword: analysis?.keywords?.primary || '',
      secondary_keywords: analysis?.keywords?.secondary || [],
      introduction: '',
      table_of_contents: [],
      sections: [],
      faq: [],
      conclusion: '',
      call_to_action: '',
      references: [],
      images: [],
      internal_links: [],
      external_links: [],
      markdown_content: content,
      word_count: content.split(/\s+/).length,
      reading_time: processedTranscript?.statistics?.estimated_read_time || transcript?.estimated_read_time || '< 1 min',
      formats: Array.from(selectedFormats),
      compress: selectedFormats.size > 1,
      base_url: window.location.origin,
    };

    try {
      const resp = await fetch('/api/blog-export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });
      const data = await resp.json();
      if (data.success) {
        const files = (data.generated_files || []).map((f: any, i: number) => ({
          format: f.format || '',
          filename: f.filename || '',
          size_display: f.size_display || f.size_display || '',
          download_url: `/api/blog-export/download/${f.filename}`,
          mime_type: f.mime_type || '',
          valid: f.valid !== false,
        }));
        setExportResult({
          success: true,
          files,
          zip_download: data.zip_download,
        });
      } else {
        setExportResult({
          success: false,
          files: [],
          error: data.error || 'Export failed',
        });
      }
    } catch (err) {
      setExportResult({
        success: false,
        files: [],
        error: err instanceof Error ? err.message : 'Export request failed',
      });
    } finally {
      setExporting(false);
    }
  }, [selectedFormats, metadata, transcript, processedTranscript, analysis]);

  const handleDownload = (url: string, filename: string) => {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleReset = () => {
    reset();
    navigate('/blog');
  };

  const handleBack = () => {
    navigate('/blog/editor');
  };

  if (!videoId) {
    navigate('/blog', { replace: true });
    return null;
  }

  const getFormatIcon = (formatId: string) => {
    const fmt = FORMATS.find((f) => f.id === formatId);
    const Icon = fmt?.icon || FileText;
    return <Icon size={16} />;
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <WorkflowHeader currentStep={state.currentStep} />

      {/* Format Selection */}
      {!exportResult && (
        <Card padding="lg" className="mb-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center shadow-lg shadow-blue-200 dark:shadow-blue-900/30">
              <Download size={20} className="text-white" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                Export Blog
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Select formats and download your blog article
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
            {FORMATS.map((fmt) => {
              const selected = selectedFormats.has(fmt.id);
              const Icon = fmt.icon;
              return (
                <button
                  key={fmt.id}
                  onClick={() => toggleFormat(fmt.id)}
                  className={`relative flex items-start gap-3 p-4 rounded-xl text-left border transition-all-200 ${
                    selected
                      ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
                      : 'bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700 hover:border-blue-200 dark:hover:border-blue-800'
                  }`}
                >
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      selected
                        ? 'bg-blue-100 dark:bg-blue-800 text-blue-600 dark:text-blue-300'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500'
                    }`}
                  >
                    <Icon size={16} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-900 dark:text-white">
                        {fmt.label}
                      </span>
                      <span className="text-[10px] font-mono text-gray-400 dark:text-gray-500">
                        {fmt.ext}
                      </span>
                      {selected && (
                        <CheckCircle2 size={14} className="text-blue-500 ml-auto" />
                      )}
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {fmt.description}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-3">
            {selectedFormats.size > 1 && (
              <div className="flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500">
                <Package size={12} />
                Files will be bundled as ZIP
              </div>
            )}
            <div className="ml-auto">
              <button
                onClick={handleExport}
                disabled={exporting || selectedFormats.size === 0}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg shadow-blue-200 dark:shadow-blue-900/30 hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all-200"
              >
                {exporting ? (
                  <>
                    <Loader2 size={15} className="animate-spin" />
                    Exporting...
                  </>
                ) : (
                  <>
                    <Download size={15} />
                    Export ({selectedFormats.size} {selectedFormats.size === 1 ? 'format' : 'formats'})
                  </>
                )}
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* Export Progress */}
      {exporting && (
        <Card padding="lg" className="mb-6">
          <div className="flex items-center gap-3 mb-4">
            <Loader2 size={18} className="animate-spin text-blue-500" />
            <div>
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                Generating Export Files
              </h4>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Creating your blog in {selectedFormats.size} format{selectedFormats.size > 1 ? 's' : ''}...
              </p>
            </div>
          </div>
          <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-2 overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full"
              initial={{ width: '0%' }}
              animate={{ width: '80%' }}
              transition={{ duration: 2, ease: 'easeInOut' }}
            />
          </div>
        </Card>
      )}

      {/* Export Results */}
      {exportResult && !exporting && (
        <Card padding="lg" className="mb-6">
          <div className="flex items-center gap-3 mb-5">
            {exportResult.success ? (
              <>
                <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-900/30 flex items-center justify-center">
                  <CheckCircle2 size={20} className="text-emerald-500" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                    Export Complete
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {exportResult.files.length} file{exportResult.files.length > 1 ? 's' : ''} generated successfully
                  </p>
                </div>
              </>
            ) : (
              <>
                <div className="w-10 h-10 rounded-xl bg-red-50 dark:bg-red-900/30 flex items-center justify-center">
                  <XCircle size={20} className="text-red-500" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                    Export Failed
                  </h3>
                  <p className="text-sm text-red-500 dark:text-red-400">
                    {exportResult.error || 'An error occurred during export'}
                  </p>
                </div>
              </>
            )}
          </div>

          {exportResult.success && (
            <>
              {/* Download All as ZIP */}
              {exportResult.zip_download && (
                <button
                  onClick={() => handleDownload(exportResult.zip_download!, 'blog-export.zip')}
                  className="w-full mb-4 inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold bg-gradient-to-r from-emerald-600 to-emerald-700 text-white shadow-lg hover:from-emerald-700 hover:to-emerald-800 transition-all-200"
                >
                  <Package size={16} />
                  Download All as ZIP
                </button>
              )}

              {/* Individual Files */}
              <div className="space-y-2">
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  Individual Files
                </button>
                {expanded && exportResult.files.map((file) => (
                  <div
                    key={file.format}
                    className="flex items-center gap-3 px-4 py-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800"
                  >
                    {getFormatIcon(file.format)}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {file.filename}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
                        <span>{file.size_display}</span>
                        {file.valid !== false && (
                          <span className="flex items-center gap-0.5 text-emerald-500">
                            <CheckCircle2 size={10} />
                            Valid
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDownload(file.download_url, file.filename)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all-200"
                    >
                      <Download size={12} />
                      Download
                    </button>
                  </div>
                ))}
              </div>

              {/* Export again */}
              <div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-800">
                <button
                  onClick={() => {
                    setExportResult(null);
                    setExporting(false);
                  }}
                  className="text-sm text-blue-500 dark:text-blue-400 hover:text-blue-600 dark:hover:text-blue-300"
                >
                  Export again with different formats
                </button>
              </div>
            </>
          )}

          {!exportResult.success && (
            <div className="mt-4">
              <button
                onClick={handleExport}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/50 transition-all-200"
              >
                <RotateCcw size={14} />
                Retry Export
              </button>
            </div>
          )}
        </Card>
      )}

      <WorkflowFooter
        currentStep={state.currentStep}
        onBack={handleBack}
        onContinue={handleReset}
        continueLabel="Start Over →"
        showReset
        onReset={handleReset}
      />
    </motion.div>
  );
}
