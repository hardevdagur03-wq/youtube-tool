import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, Youtube, Hash, FileSpreadsheet, Loader2, CheckCircle2, XCircle, AlertCircle, ArrowLeft } from 'lucide-react';
import type { ProgressData, ResultData } from '../types';

interface ExportFormProps {
  onExport: (channel: string, limit: number) => void;
  loading: boolean;
  progress: ProgressData | null;
  result: ResultData | null;
  error: string | null;
  reset: () => void;
}

export default function ExportForm({ onExport, loading, progress, result, error, reset }: ExportFormProps) {
  const [channel, setChannel] = useState('');
  const [limit, setLimit] = useState('0');
  const [touched, setTouched] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (!channel.trim()) return;
    onExport(channel.trim(), Math.max(0, parseInt(limit) || 0));
  };

  const isActive = loading || progress || result || error;

  return (
    <section id="export-form" className="relative z-10 -mt-8 pb-12 sm:pb-16">
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
              <div className="bg-white rounded-3xl shadow-elevated p-6 sm:p-8 border border-gray-100">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center flex-shrink-0">
                    <Download size={18} className="text-emerald-600" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-gray-900">Export Channel Videos</h3>
                    <p className="text-sm text-gray-500">Enter a YouTube channel URL, handle, or channel ID</p>
                  </div>
                </div>

                <form onSubmit={handleSubmit}>
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Channel</label>
                    <div className="relative">
                      <Youtube size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input
                        type="text"
                        value={channel}
                        onChange={(e) => setChannel(e.target.value)}
                        placeholder="@physicsgalaxyworld or UCgBmfNILAlXmGv3CsJ8oFJA"
                        className={`w-full pl-10 pr-4 py-3 rounded-xl border-2 text-sm transition-all-200 outline-none ${
                          touched && !channel.trim()
                            ? 'border-red-300 focus:border-red-400 focus:ring-4 focus:ring-red-100'
                            : 'border-gray-200 focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100'
                        }`}
                        autoFocus
                      />
                    </div>
                    {touched && !channel.trim() && (
                      <p className="text-xs text-red-500 mt-1.5">Please enter a channel URL, handle, or ID</p>
                    )}
                  </div>

                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Video limit <span className="text-gray-400 font-normal">(0 = all)</span>
                    </label>
                    <div className="relative">
                      <Hash size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input
                        type="number"
                        value={limit}
                        onChange={(e) => setLimit(e.target.value)}
                        min={0}
                        className="w-full pl-10 pr-4 py-3 rounded-xl border-2 border-gray-200 text-sm transition-all-200 outline-none focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="relative overflow-hidden w-full inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 text-white font-semibold text-sm shadow-lg shadow-emerald-200 hover:shadow-xl hover:shadow-emerald-200 hover:scale-[1.01] active:scale-[0.99] transition-all-200"
                  >
                    <FileSpreadsheet size={16} />
                    Export to CSV
                  </button>
                </form>
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>

        {/* Progress */}
        <AnimatePresence>
          {progress && !result && !error && (
            <motion.div
              key="progress"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="bg-white rounded-3xl shadow-elevated p-8 border border-gray-100 text-center"
            >
              <div className="w-14 h-14 rounded-full bg-emerald-50 flex items-center justify-center mx-auto mb-4">
                <Loader2 size={28} className="text-emerald-500 animate-spin" />
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-1">Fetching videos...</h4>
              <p className="text-sm text-gray-500 mb-6">
                {progress.steps.filter((s) => s.status === 'running').map((s) => s.name).join(', ') || 'Starting pipeline'}
              </p>
              <div className="max-w-md mx-auto">
                <div className="bg-gray-50 rounded-xl p-1 border border-gray-100">
                  {progress.steps.map((step, i) => (
                    <div key={i} className="flex items-center gap-3 px-4 py-2.5 text-sm border-b border-gray-100 last:border-0">
                      {step.status === 'running' ? (
                        <Loader2 size={14} className="text-emerald-500 animate-spin flex-shrink-0" />
                      ) : step.status === 'ok' ? (
                        <CheckCircle2 size={14} className="text-emerald-500 flex-shrink-0" />
                      ) : step.status === 'error' ? (
                        <XCircle size={14} className="text-red-500 flex-shrink-0" />
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-full border-2 border-gray-300 flex-shrink-0" />
                      )}
                      <span className={step.status === 'error' ? 'text-red-600' : 'text-gray-700'}>{step.name}</span>
                      {step.detail && <span className="text-gray-400 text-xs ml-auto">{step.detail}</span>}
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Result */}
        <AnimatePresence>
          {result && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              {result.success ? (
                <div className="bg-white rounded-3xl shadow-elevated border border-gray-100 overflow-hidden">
                  <div className="p-6 sm:p-8">
                    <div className="flex items-start justify-between flex-wrap gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <CheckCircle2 size={18} className="text-emerald-500" />
                          <h4 className="text-lg font-semibold text-gray-900">{result.channel_title}</h4>
                        </div>
                        <p className="text-sm font-mono text-gray-400">{result.channel_id}</p>
                      </div>
                      <a
                        href={`/api/download/${result.run_id || ''}`}
                        id="download-link"
                        download="videos.csv"
                        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 text-white font-semibold text-sm shadow-lg shadow-emerald-200 hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all-200 no-underline"
                      >
                        <Download size={15} />
                        Download CSV
                      </a>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 border-t border-gray-100">
                    {[
                      { label: 'Videos Exported', value: result.total_videos?.toLocaleString() || '0' },
                      { label: 'Total Discovered', value: result.total_discovered?.toLocaleString() || '0' },
                      { label: 'API Calls', value: result.total_api_calls || '0' },
                      { label: 'File Size', value: result.file_size_bytes ? `${(result.file_size_bytes / 1024).toFixed(0)} KB` : '0 KB' },
                    ].map((stat, i) => (
                      <div key={i} className="p-5 text-center border-r border-gray-100 last:border-r-0">
                        <div className="text-2xl font-bold text-gray-900 mb-0.5">{stat.value}</div>
                        <div className="text-xs text-gray-500 font-medium">{stat.label}</div>
                      </div>
                    ))}
                  </div>
                  <div className="px-6 sm:px-8 py-4 bg-gray-50 border-t border-gray-100 flex justify-center">
                    <button onClick={reset} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
                      <ArrowLeft size={14} /> Export another channel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="bg-white rounded-3xl shadow-elevated p-8 border border-red-100 text-center">
                  <div className="w-14 h-14 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
                    <AlertCircle size={28} className="text-red-500" />
                  </div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-1">Export failed</h4>
                  <p className="text-sm text-gray-500 mb-6">{result.error || 'An unexpected error occurred.'}</p>
                  <button onClick={reset} className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border-2 border-gray-200 text-gray-700 font-semibold text-sm hover:bg-gray-50 transition-all-200">
                    Try Again
                  </button>
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
              className="bg-white rounded-3xl shadow-elevated p-8 border border-red-100 text-center"
            >
              <div className="w-14 h-14 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
                <AlertCircle size={28} className="text-red-500" />
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-1">Export failed</h4>
              <p className="text-sm text-gray-500 mb-6">{error}</p>
              <button onClick={reset} className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border-2 border-gray-200 text-gray-700 font-semibold text-sm hover:bg-gray-50 transition-all-200">
                Try Again
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
