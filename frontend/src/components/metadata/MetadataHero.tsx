import { motion } from 'framer-motion';
import { Download, BarChart3, Database, ArrowDown } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '../ui';

const features = [
  { icon: Download, label: 'CSV Export' },
  { icon: BarChart3, label: 'Metadata' },
  { icon: Database, label: 'Pagination' },
];

export default function MetadataHero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-emerald-600 via-emerald-500 to-emerald-700 dark:from-emerald-800 dark:via-emerald-700 dark:to-emerald-900 min-h-[420px] lg:min-h-[400px]">
      <div className="absolute inset-0 grid-pattern" />
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-white/5" />
      <div className="absolute top-1/4 left-1/3 w-[600px] h-[600px] bg-white/5 rounded-full blur-3xl" />
      <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-emerald-300/10 rounded-full blur-2xl" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-28 lg:pt-32 pb-10 lg:pb-14">
        <div className="flex flex-col lg:flex-row lg:items-center gap-8 lg:gap-16">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="flex-1 max-w-xl"
          >
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 text-xs text-white/70 hover:text-white transition-colors mb-4 no-underline"
            >
              <ArrowDown size={12} className="rotate-90" />
              Back to Home
            </Link>

            <Badge variant="info">YouTube Data API v3</Badge>

            <h1 className="text-[36px] sm:text-[44px] lg:text-[52px] font-extrabold leading-[1.08] tracking-[-0.03em] text-white mt-4 mb-3">
              Export YouTube Channel Videos to CSV
            </h1>

            <p className="text-[17px] leading-relaxed text-white/75 max-w-[480px] mb-6">
              Discover every uploaded public video from any YouTube channel, fetch full metadata, and export a structured CSV — all in one automated workflow.
            </p>

            <div className="flex flex-wrap gap-3 mb-6">
              {features.map((f) => (
                <div
                  key={f.label}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/10 border border-white/20 text-white/80 text-xs font-medium"
                >
                  <f.icon size={12} />
                  {f.label}
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="flex-shrink-0 hidden lg:block"
          >
            <div className="w-[380px] animate-float">
              <div className="bg-white/70 dark:bg-gray-900/70 backdrop-blur-xl rounded-2xl p-6 shadow-glass border border-white/30 dark:border-gray-700/50">
                <div className="flex items-center gap-2.5 mb-5">
                  <img src="/static/logo.png" alt="Logo" className="w-7 h-7 rounded-md" />
                  <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">videos.csv</span>
                  <span className="ml-auto px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 text-[11px] font-semibold">
                    &#10003; Export Ready
                  </span>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3 border border-gray-100 dark:border-gray-700">
                  <div className="flex justify-between text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider pb-2.5 border-b border-gray-200 dark:border-gray-700 mb-2">
                    <span className="w-20">video_id</span>
                    <span className="w-28">title</span>
                    <span className="w-14 text-right">views</span>
                    <span className="w-14 text-right">likes</span>
                  </div>
                  {[
                    { id: 'abc123', title: 'Python Tutorial', views: '25K', likes: '1.2K' },
                    { id: 'xyz456', title: 'SQL Shorts', views: '150K', likes: '8.5K' },
                    { id: 'def789', title: 'Docker Deep Dive', views: '42K', likes: '3.1K' },
                    { id: 'ghi012', title: 'React Hooks', views: '89K', likes: '5.6K' },
                  ].map((row, i) => (
                    <div
                      key={i}
                      className="flex justify-between text-xs py-1.5 text-gray-700 dark:text-gray-300 border-b border-gray-100 dark:border-gray-700 last:border-0"
                    >
                      <span className="w-20 font-mono text-gray-500 dark:text-gray-400">{row.id}</span>
                      <span className="w-28 truncate">{row.title}</span>
                      <span className="w-14 text-right text-gray-500 dark:text-gray-400">{row.views}</span>
                      <span className="w-14 text-right text-gray-500 dark:text-gray-400">{row.likes}</span>
                    </div>
                  ))}
                  <div className="flex justify-between mt-2 pt-2 border-t border-gray-200 dark:border-gray-700 text-[10px] text-gray-400 dark:text-gray-500">
                    <span>5,695 rows</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-semibold">&#10003; exported</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
