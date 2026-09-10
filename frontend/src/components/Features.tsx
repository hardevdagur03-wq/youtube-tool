import { motion } from 'framer-motion';
import { Search, Film, ListOrdered, FileDown } from 'lucide-react';

const features = [
  {
    icon: Search,
    title: 'Discover Channel',
    description: 'Resolves any YouTube channel URL, handle, or channel ID to retrieve the canonical channel ID and title using the YouTube Data API.',
    color: 'bg-blue-50 text-blue-600',
  },
  {
    icon: Film,
    title: 'Fetch Metadata',
    description: 'Retrieves full metadata for every video — title, upload date, views, likes, duration, and comments count.',
    color: 'bg-purple-50 text-purple-600',
  },
  {
    icon: ListOrdered,
    title: 'Pagination',
    description: 'Automatically walks through all pages of the uploads feed to discover every public video, supporting channels with thousands of videos.',
    color: 'bg-amber-50 text-amber-600',
  },
  {
    icon: FileDown,
    title: 'Export CSV',
    description: 'Transforms raw API data into a clean, structured CSV file with video type detection (Video/Short) and YouTube URL generation.',
    color: 'bg-emerald-50 text-emerald-600',
  },
];

export default function Features() {
  return (
    <section id="how-it-works" className="py-16 sm:py-20 bg-[#F8FAFC]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-semibold mb-4">
            Pipeline
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900 tracking-tight mb-3">
            How It Works
          </h2>
          <p className="text-[17px] text-gray-500 max-w-xl mx-auto">
            The pipeline automates the entire workflow from channel resolution to CSV export — no manual steps required.
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-80px' }}
              transition={{ duration: 0.5, delay: i * 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="group bg-white rounded-2xl p-6 border border-gray-100 shadow-card hover:shadow-card-hover hover:-translate-y-0.5 transition-all-300"
            >
              <div className={`w-10 h-10 rounded-xl ${feature.color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform-200`}>
                <feature.icon size={20} />
              </div>
              <h3 className="text-base font-semibold text-gray-900 mb-2">{feature.title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{feature.description}</p>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.5, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="mt-10 bg-white rounded-2xl p-6 sm:p-8 border border-gray-100 shadow-card"
        >
          <h3 className="text-base font-semibold text-gray-900 mb-4">CSV Output Format</h3>
          <div className="overflow-x-auto rounded-xl border border-gray-100">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  {['Column', 'Description'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  ['video_id', 'Unique YouTube Video ID'],
                  ['title', 'Video title'],
                  ['upload_date', 'Video publish date'],
                  ['views', 'Total views'],
                  ['likes', 'Total likes'],
                  ['duration', 'Duration (HH:MM:SS)'],
                  ['video_type', 'Video or Short'],
                ].map(([col, desc]) => (
                  <tr key={col} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50">
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-700">{col}</td>
                    <td className="px-4 py-2.5 text-gray-500">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
