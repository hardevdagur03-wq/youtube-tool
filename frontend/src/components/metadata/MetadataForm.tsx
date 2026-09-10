import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Download, Youtube, Hash, FileSpreadsheet, Loader2,
  CheckCircle2, XCircle, AlertCircle, ArrowLeft, Wifi, WifiOff,
  Clock, Play, X as XIcon, RotateCcw, BarChart3,
} from 'lucide-react';
import type { V3ExportProgress, V3ExportResult, StageProgress } from '../../types';

const STAGE_LABELS: Record<string, string> = {
  validate_url: 'Validate URL',
  check_cache: 'Check Cache',
  resolve_channel: 'Resolve Channel',
  fetch_playlist: 'Fetch Upload Playlist',
  fetch_video_ids: 'Fetch Video IDs',
  fetch_metadata: 'Fetch Metadata',
  generate_csv: 'Generate CSV',
  complete: 'Completed',
  error: 'Error',
};

const STAGE_ORDER = [
  'validate_url', 'check_cache', 'resolve_channel',
  'fetch_playlist', 'fetch_video_ids', 'fetch_metadata',
  'generate_csv', 'complete',
];

interface MetadataFormProps {
  onExport: (channel: string, limit: number) => void;
  loading: boolean;
  progress: V3ExportProgress | null;
  result: V3ExportResult | null;
  error: string | null;
  reset: () => void;
  retry?: () => void;
  cancelExport?: () => void;
  backendStatus?: 'unknown' | 'ok' | 'error';
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

function getStageStatusIcon(stage: StageProgress, isCurrent: boolean) {
  if (stage.error) return <XCircle size={14} className="text-red-500 flex-shrink-0" />;
  if (stage.status === 'completed') return <CheckCircle2 size={14} className="text-emerald-500 flex-shrink-0" />;
  if (stage.status === 'running' || isCurrent) return <Loader2 size={14} className="text-blue-500 animate-spin flex-shrink-0" />;
  if (stage.status === 'failed') return <XCircle size={14} className="text-red-500 flex-shrink-0" />;
  return <div className="w-3.5 h-3.5 rounded-full border-2 border-gray-300 dark:border-gray-600 flex-shrink-0" />;
}

export default function MetadataForm({
  onExport, loading, progress, result, error, reset, retry, cancelExport, backendStatus = 'unknown',
}: MetadataFormProps) {
  const [channel, setChannel] = useState('');
  const [limit, setLimit] = useState('0');
  const [touched, setTouched] = useState(false);
  const [channelError, setChannelError] = useState<string | null>(null);

  const validateChannel = (value: string): string | null => {
    const trimmed = value.trim();
    if (!trimmed) return 'Please enter a channel URL, handle, or ID.';
    if (
      trimmed.startsWith('@') || trimmed.startsWith('UC') ||
      trimmed.startsWith('http://') || trimmed.startsWith('https://') ||
      /^[a-zA-Z0-9._-]{3,30}$/.test(trimmed)
    ) return null;
    return 'Invalid format. Enter a handle (@channel), channel ID (UC...), or YouTube URL.';
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setTouched(true);
    const err = validateChannel(channel);
    setChannelError(err);
    if (err) return;
    onExport(channel.trim(), Math.max(0, parseInt(limit) || 0));
  };

  const handleChannelChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setChannel(e.target.value);
    if (touched) setChannelError(validateChannel(e.target.value));
  };

  const isActive = loading || progress || result || error;
  const currentStageKey = progress?.current_stage || '';
  const stages = progress?.stages || {};

  const total_discovered = stages['fetch_video_ids']?.total || 0;
  const processed = stages['fetch_metadata']?.processed || 0;
  const remaining = stages['fetch_metadata']?.remaining || 0;
  const api_calls = stages['fetch_metadata']?.api_calls || 0;
  const rows_written = stages['fetch_metadata']?.rows_written || 0;
  const current_page = stages['fetch_metadata']?.current_page || 0;
  const total_pages = stages['fetch_metadata']?.total_pages || 0;

  const elapsed = progress?.elapsed_seconds || 0;
  const eta = progress?.eta_seconds || 0;
  const progressPct = progress?.overall_progress_pct || 0;

  const downloadUrl = result?.result?.success ? `/api/export/${result.result.job_id}/download` : null;

  return (
    <section className="relative z-10 -mt-8 pb-12 sm:pb-16">
      <div className="max-w-2xl mx-auto px-4 sm:px-6">
        <AnimatePresence mode="wait">
          {!isActive ? (
            <motion.div
              key="form"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-elevated p-6 sm:p-8 border border-gray-100 dark:border-gray-800">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-900/30 flex items-center justify-center flex-shrink-0">
                    <Download size={18} className="text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-gray-900 dark:text-white">Export Channel Videos</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Enter a YouTube channel URL, handle, or channel ID</p>
                  </div>
                </div>
                <form onSubmit={handleSubmit}>
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Channel</label>
                    <div className="relative">
                      <Youtube size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input type="text" value={channel} onChange={handleChannelChange}
                        placeholder="@physicsgalaxyworld or UCgBmfNILAlXmGv3CsJ8oFJA"
                        className={`w-full pl-10 pr-4 py-3 rounded-xl border-2 text-sm transition-all-200 outline-none bg-white dark:bg-gray-800 ${
                          touched && channelError
                            ? 'border-red-300 dark:border-red-700 focus:border-red-400 focus:ring-4 focus:ring-red-100'
                            : 'border-gray-200 dark:border-gray-700 focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100'
                        }`}
                        autoFocus
                      />
                    </div>
                    {touched && channelError && <p className="text-xs text-red-500 mt-1.5">{channelError}</p>}
                  </div>
                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                      Video limit <span className="text-gray-400 font-normal">(0 = all)</span>
                    </label>
                    <div className="relative">
                      <Hash size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input type="number" value={limit} onChange={(e) => setLimit(e.target.value)}
                        min={0}
                        className="w-full pl-10 pr-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm transition-all-200 outline-none focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100"
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mb-3 text-xs">
                    {backendStatus === 'ok' ? (
                      <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                        <Wifi size={12} /> Backend connected
                      </span>
                    ) : backendStatus === 'error' ? (
                      <span className="flex items-center gap-1 text-red-500">
                        <WifiOff size={12} /> Backend unreachable
                      </span>
                    ) : null}
                  </div>
                  <button type="submit" disabled={loading}
                    className="relative overflow-hidden w-full inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 text-white font-semibold text-sm shadow-lg shadow-emerald-200 hover:shadow-xl hover:scale-[1.01] active:scale-[0.99] transition-all-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? <Loader2 size={16} className="animate-spin" /> : <FileSpreadsheet size={16} />}
                    {loading ? 'Starting...' : 'Export to CSV'}
                  </button>
                </form>
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>

        {/* Enhanced Progress UI */}
        <AnimatePresence>
          {progress && !result && !error && (
            <motion.div
              key="progress"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="bg-white dark:bg-gray-900 rounded-3xl shadow-elevated p-6 sm:p-8 border border-gray-100 dark:border-gray-800"
            >
              {/* Progress Bar */}
              <div className="mb-6">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {progressPct >= 100 ? (
                      <CheckCircle2 size={18} className="text-emerald-500" />
                    ) : (
                      <Loader2 size={18} className="text-blue-500 animate-spin" />
                    )}
                    <span className="text-sm font-semibold text-gray-900 dark:text-white">
                      {progressPct >= 100 ? 'Complete' : STAGE_LABELS[currentStageKey] || 'Processing...'}
                    </span>
                  </div>
                  <span className="text-sm font-bold text-gray-900 dark:text-white">
                    {Math.round(progressPct)}%
                  </span>
                </div>
                <div className="w-full h-3 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-blue-500 to-emerald-500 rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, progressPct)}%` }}
                    transition={{ duration: 0.5, ease: 'easeOut' }}
                  />
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3 text-center">
                  <div className="text-lg font-bold text-gray-900 dark:text-white">
                    {total_discovered.toLocaleString()}
                  </div>
                  <div className="text-[10px] text-gray-500 dark:text-gray-400 uppercase tracking-wider font-medium">Videos Found</div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3 text-center">
                  <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                    {processed.toLocaleString()}
                  </div>
                  <div className="text-[10px] text-gray-500 dark:text-gray-400 uppercase tracking-wider font-medium">Processed</div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3 text-center">
                  <div className="text-lg font-bold text-amber-600 dark:text-amber-400">
                    {remaining.toLocaleString()}
                  </div>
                  <div className="text-[10px] text-gray-500 dark:text-gray-400 uppercase tracking-wider font-medium">Remaining</div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3 text-center">
                  <div className="text-lg font-bold text-gray-900 dark:text-white">
                    {eta > 0 ? formatTime(eta) : '--'}
                  </div>
                  <div className="text-[10px] text-gray-500 dark:text-gray-400 uppercase tracking-wider font-medium">ETA</div>
                </div>
              </div>

              {/* Additional Stats */}
              <div className="flex flex-wrap gap-2 mb-5 text-xs text-gray-500 dark:text-gray-400">
                <span className="flex items-center gap-1"><BarChart3 size={12} /> Page {current_page}/{total_pages}</span>
                <span className="flex items-center gap-1"><Clock size={12} /> Elapsed: {formatTime(elapsed)}</span>
                <span className="flex items-center gap-1">API: {api_calls} calls</span>
                <span className="flex items-center gap-1">Rows: {rows_written}</span>
              </div>

              {/* Timeline */}
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-1 border border-gray-100 dark:border-gray-700 mb-4">
                {STAGE_ORDER.filter(k => stages[k]).map((key) => {
                  const stage = stages[key];
                  const isCurrent = key === currentStageKey;
                  const stagePct = key === 'fetch_metadata' ? stage.progress_pct : (stage.status === 'completed' ? 100 : 0);
                  return (
                    <div key={key}
                      className={`flex items-center gap-3 px-4 py-2.5 text-sm border-b border-gray-100 dark:border-gray-700 last:border-0 ${
                        isCurrent ? 'bg-blue-50 dark:bg-blue-900/20 rounded-lg' : ''
                      }`}
                    >
                      {getStageStatusIcon(stage, isCurrent)}
                      <span className={`text-sm ${stage.error ? 'text-red-600' : stage.status === 'completed' ? 'text-gray-700 dark:text-gray-300' : isCurrent ? 'text-blue-700 dark:text-blue-300 font-medium' : 'text-gray-500 dark:text-gray-400'}`}>
                        {STAGE_LABELS[key] || key}
                      </span>
                      {key === 'fetch_metadata' && stage.total > 0 && (
                        <span className="text-xs text-gray-400 ml-auto">
                          {stage.processed}/{stage.total}
                        </span>
                      )}
                      {stage.detail && !stage.error && (
                        <span className="text-xs text-gray-400 ml-auto">{stage.detail}</span>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Cancel Button */}
              {cancelExport && (
                <button onClick={cancelExport}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border-2 border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm font-semibold hover:bg-red-50 dark:hover:bg-red-900/20 transition-all-200"
                >
                  <XIcon size={14} /> Cancel Export
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Result */}
        <AnimatePresence>
          {result && (
            <motion.div key="result" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
              {result.result?.success ? (
                <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-elevated border border-gray-100 dark:border-gray-800 overflow-hidden">
                  <div className="p-6 sm:p-8">
                    <div className="flex items-start justify-between flex-wrap gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <CheckCircle2 size={18} className="text-emerald-500" />
                          <h4 className="text-lg font-semibold text-gray-900 dark:text-white">{result.result.channel_title}</h4>
                        </div>
                        <p className="text-sm font-mono text-gray-400">{result.result.channel_id}</p>
                      </div>
                      {downloadUrl && (
                        <a href={downloadUrl} download="videos.csv"
                          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 text-white font-semibold text-sm shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all-200 no-underline"
                        >
                          <Download size={15} /> Download CSV
                        </a>
                      )}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 border-t border-gray-100 dark:border-gray-800">
                    {[
                      { label: 'Videos Exported', value: result.result.total_videos?.toLocaleString() || '0' },
                      { label: 'Total Discovered', value: result.result.total_discovered?.toLocaleString() || '0' },
                      { label: 'API Calls', value: result.result.total_api_calls || '0' },
                      { label: 'File Size', value: result.result.file_size_bytes ? `${(result.result.file_size_bytes / 1024).toFixed(0)} KB` : '0 KB' },
                    ].map((stat, i) => (
                      <div key={i} className="p-5 text-center border-r border-gray-100 last:border-r-0">
                        <div className="text-2xl font-bold text-gray-900 dark:text-white mb-0.5">{stat.value}</div>
                        <div className="text-xs text-gray-500 font-medium">{stat.label}</div>
                      </div>
                    ))}
                  </div>
                  <div className="px-6 sm:px-8 py-4 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-100 dark:border-gray-800 flex justify-center">
                    <button onClick={reset}
                      className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                    >
                      <ArrowLeft size={14} /> Export another channel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-elevated p-8 border border-red-100 dark:border-red-900/50 text-center">
                  <div className="w-14 h-14 rounded-full bg-red-50 dark:bg-red-900/30 flex items-center justify-center mx-auto mb-4">
                    <AlertCircle size={28} className="text-red-500" />
                  </div>
                  <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Export failed</h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">{result.result?.error || result.result?.error_type || result.error || 'Export failed for an unknown reason.'}</p>
                  {result.result?.error_type && (
                    <p className="text-xs text-gray-400 mb-4">Error type: {result.result.error_type}</p>
                  )}
                  <div className="flex justify-center gap-3">
                    <button onClick={reset}
                      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border-2 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-semibold text-sm hover:bg-gray-50 transition-all-200"
                    >
                      <RotateCcw size={14} /> Try Again
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error */}
        <AnimatePresence>
          {error && !result && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="bg-white dark:bg-gray-900 rounded-3xl shadow-elevated p-8 border border-red-100 dark:border-red-900/50 text-center"
            >
              <div className="w-14 h-14 rounded-full bg-red-50 dark:bg-red-900/30 flex items-center justify-center mx-auto mb-4">
                <AlertCircle size={28} className="text-red-500" />
              </div>
              <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Export failed</h4>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">{error}</p>
              <div className="flex justify-center gap-3">
                <button onClick={reset}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border-2 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-semibold text-sm hover:bg-gray-50 transition-all-200"
                >
                  <RotateCcw size={14} /> Try Again
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
