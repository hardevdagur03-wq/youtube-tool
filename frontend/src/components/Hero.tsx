import { motion } from 'framer-motion';
import { Download, Play, BarChart3, Database, ArrowDown } from 'lucide-react';

const features = [
  { icon: Download, label: 'CSV Export' },
  { icon: BarChart3, label: 'Metadata' },
  { icon: Database, label: 'Pagination' },
];

export default function Hero() {
  return (
    <section id="hero" className="relative overflow-hidden hero-gradient min-h-[520px] lg:min-h-[460px]">
      <div className="absolute inset-0 grid-pattern" />
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-white/5" />
      <div className="absolute top-1/4 left-1/3 w-[600px] h-[600px] bg-white/5 rounded-full blur-3xl" />
      <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-emerald-300/10 rounded-full blur-2xl" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 lg:pt-28 pb-10 lg:pb-14">
        <div className="flex flex-col lg:flex-row lg:items-center gap-8 lg:gap-16">

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="flex-1 max-w-xl"
          >
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/20 text-white/90 text-xs font-medium mb-5">
              <Play size={12} fill="currentColor" />
              YouTube Data API v3
            </div>

            <h1 className="text-[40px] sm:text-[48px] lg:text-[56px] font-extrabold leading-[1.08] tracking-[-0.03em] text-white mb-4">
              Export YouTube Channel Videos to CSV
            </h1>

            <p className="text-[17px] leading-relaxed text-white/75 max-w-[480px] mb-6">
              Discover every uploaded public video from any YouTube channel, fetch full metadata, and export a structured CSV — all in one automated workflow.
            </p>

            <div className="flex flex-wrap gap-3 mb-8">
              {features.map((f) => (
                <div key={f.label} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/8 border border-white/15 text-white/80 text-xs font-medium">
                  <f.icon size={12} />
                  {f.label}
                </div>
              ))}
            </div>

            <div className="flex flex-wrap gap-3">
              <a href="#export-form" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white text-emerald-700 font-semibold text-sm shadow-lg shadow-emerald-900/20 hover:shadow-xl hover:shadow-emerald-900/25 hover:scale-[1.02] active:scale-[0.98] transition-all-200 no-underline">
                <Download size={16} />
                Export Now
              </a>
              <a href="#how-it-works" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white/10 border border-white/20 text-white font-medium text-sm hover:bg-white/15 hover:border-white/30 transition-all-200 no-underline">
                <ArrowDown size={16} />
                How It Works
              </a>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="flex-shrink-0 hidden lg:block"
          >
            <div className="w-[380px] animate-float">
              <div className="glass-card rounded-2xl p-6 shadow-glass">
                <div className="flex items-center gap-2.5 mb-5">
                  <img src="/static/logo.png" alt="Matrix" className="w-7 h-7 rounded-md" />
                  <span className="text-sm font-semibold text-gray-800">videos.csv</span>
                  <span className="ml-auto px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-[11px] font-semibold">&#10003; Export Ready</span>
                </div>
                <div className="bg-[#F8FAFC] rounded-xl p-3 border border-gray-100">
                  <div className="flex justify-between text-[10px] font-semibold text-gray-400 uppercase tracking-wider pb-2.5 border-b border-gray-200 mb-2">
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
                    <div key={i} className="flex justify-between text-xs py-1.5 text-gray-700 border-b border-gray-100 last:border-0">
                      <span className="w-20 font-mono text-gray-500">{row.id}</span>
                      <span className="w-28 truncate">{row.title}</span>
                      <span className="w-14 text-right text-gray-500">{row.views}</span>
                      <span className="w-14 text-right text-gray-500">{row.likes}</span>
                    </div>
                  ))}
                  <div className="flex justify-between mt-2 pt-2 border-t border-gray-200 text-[10px] text-gray-400">
                    <span>5,695 rows</span>
                    <span className="text-emerald-600 font-semibold">&#10003; exported</span>
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
