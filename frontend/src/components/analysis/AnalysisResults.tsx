import { motion } from 'framer-motion';
import {
  Target, Lightbulb, TrendingUp, Users, BookOpen, BarChart3, Layers,
  MessageSquare, Award, FileText, CheckCircle, Zap, Hash, Braces,
} from 'lucide-react';
import type { ContentAnalysisResult } from '../../types';

interface Props {
  analysis: ContentAnalysisResult;
}

export default function AnalysisResults({ analysis }: Props) {
  const a = analysis;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      {/* Primary Topic + Category Header */}
      <div className="rounded-xl border border-indigo-100 dark:border-indigo-900/30 bg-white dark:bg-gray-900 p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
              <Target size={12} />
              Primary Topic
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white break-words">
              {a.primary_topic || 'Not detected'}
            </h2>
            {a.secondary_topics.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-3">
                {a.secondary_topics.map((t, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                    {t}
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="flex gap-2 shrink-0">
            <span className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-violet-50 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 capitalize">
              {a.category}
            </span>
            <span className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 capitalize">
              {a.search_intent}
            </span>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SummaryCard icon={Lightbulb} label="Short Summary" value={a.summary.short} />
        <SummaryCard icon={MessageSquare} label="Executive Summary" value={a.summary.executive} />
        <SummaryCard icon={FileText} label="Content Purpose" value={a.content_purpose} />
      </div>

      {/* Keywords Section */}
      <SectionCard icon={Hash} title="Keywords" color="indigo">
        <div className="space-y-3">
          <div>
            <span className="text-xs text-gray-500 uppercase tracking-wider font-medium">Primary</span>
            <div className="mt-1">
              <span className="inline-flex px-3 py-1 rounded-lg bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-200 font-semibold text-sm">
                {a.keywords.primary || 'N/A'}
              </span>
            </div>
          </div>
          {a.keywords.secondary.length > 0 && (
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wider font-medium">Secondary</span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {a.keywords.secondary.map((k, i) => (
                  <span key={i} className="px-2 py-0.5 rounded-md text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
                    {k}
                  </span>
                ))}
              </div>
            </div>
          )}
          {a.keywords.long_tail.length > 0 && (
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wider font-medium">Long-tail</span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {a.keywords.long_tail.map((k, i) => (
                  <span key={i} className="px-2 py-0.5 rounded-md text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 italic">
                    {k}
                  </span>
                ))}
              </div>
            </div>
          )}
          {a.keywords.lsi.length > 0 && (
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wider font-medium">LSI</span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {a.keywords.lsi.map((k, i) => (
                  <span key={i} className="px-2 py-0.5 rounded-md text-xs bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300">
                    {k}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </SectionCard>

      {/* Entities Section */}
      {hasEntities(a.entities) && (
        <SectionCard icon={Users} title="Entities Detected" color="violet">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {renderEntityGroup('People', a.entities.people)}
            {renderEntityGroup('Companies', a.entities.companies)}
            {renderEntityGroup('Technologies', a.entities.technologies)}
            {renderEntityGroup('Programming Languages', a.entities.programming_languages)}
            {renderEntityGroup('Products', a.entities.products)}
            {renderEntityGroup('Frameworks', a.entities.frameworks)}
            {renderEntityGroup('Tools', a.entities.tools)}
            {renderEntityGroup('Organizations', a.entities.organizations)}
            {renderEntityGroup('Countries', a.entities.countries)}
          </div>
        </SectionCard>
      )}

      {/* Outline Section */}
      {a.outline.sections.length > 0 && (
        <SectionCard icon={Layers} title="Content Outline" color="emerald">
          <ol className="space-y-2">
            {a.outline.sections.map((section, i) => (
              <li key={i} className="flex items-start gap-3 text-sm">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 font-bold text-xs shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <span className="text-gray-800 dark:text-gray-200">{section}</span>
              </li>
            ))}
          </ol>
        </SectionCard>
      )}

      {/* Audience & Intent */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SectionCard icon={TrendingUp} title="Audience & Intent" color="amber">
          <div className="space-y-2 text-sm">
            <Row label="Target Audience" value={a.target_audience} />
            <Row label="Experience Level" value={a.experience_level} />
            <Row label="Industry" value={a.industry} />
            <Row label="Difficulty" value={a.difficulty} />
            <Row label="Intent Confidence" value={`${(a.intent_confidence * 100).toFixed(0)}%`} />
          </div>
        </SectionCard>
        <SectionCard icon={Award} title="Key Takeaways" color="amber">
          <ul className="space-y-1.5">
            {a.key_takeaways.length > 0 ? a.key_takeaways.map((t, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <CheckCircle size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                <span className="text-gray-700 dark:text-gray-300">{t}</span>
              </li>
            )) : (
              <li className="text-sm text-gray-400">No takeaways extracted</li>
            )}
          </ul>
        </SectionCard>
      </div>

      {/* Action Items */}
      {a.action_items.length > 0 && (
        <SectionCard icon={Zap} title="Action Items" color="blue">
          <ul className="space-y-1.5">
            {a.action_items.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <span className="text-gray-700 dark:text-gray-300">{item}</span>
              </li>
            ))}
          </ul>
        </SectionCard>
      )}

      {/* Quality Scores */}
      <SectionCard icon={BarChart3} title="Quality Scores" color="indigo">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <ScoreBar label="Depth" value={a.quality.depth_score} />
          <ScoreBar label="SEO Potential" value={a.quality.seo_potential} />
          <ScoreBar label="Evergreen" value={a.quality.evergreen_score} />
          <ScoreBar label="Educational" value={a.quality.educational_value} />
          <ScoreBar label="Engagement" value={a.quality.engagement_potential} />
        </div>
        <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between text-sm">
          <span className="text-gray-500">Overall Confidence</span>
          <span className="font-bold text-lg text-indigo-600 dark:text-indigo-400">
            {(a.quality.confidence * 100).toFixed(0)}%
          </span>
        </div>
      </SectionCard>

      {/* Bullet Points */}
      {a.summary.bullet_points.length > 0 && (
        <SectionCard icon={Braces} title="Key Points" color="gray">
          <ul className="space-y-1.5">
            {a.summary.bullet_points.map((point, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-gray-400 mt-2 shrink-0" />
                <span className="text-gray-700 dark:text-gray-300">{point}</span>
              </li>
            ))}
          </ul>
        </SectionCard>
      )}
    </motion.div>
  );
}

function SummaryCard({ icon: Icon, label, value }: { icon: any; label: string; value: string }) {
  if (!value) return null;
  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
      <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
        <Icon size={12} />
        {label}
      </div>
      <p className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">{value}</p>
    </div>
  );
}

function SectionCard({ icon: Icon, title, color, children }: { icon: any; title: string; color: string; children: React.ReactNode }) {
  const colorMap: Record<string, string> = {
    indigo: 'border-indigo-100 dark:border-indigo-900/30',
    violet: 'border-violet-100 dark:border-violet-900/30',
    emerald: 'border-emerald-100 dark:border-emerald-900/30',
    amber: 'border-amber-100 dark:border-amber-900/30',
    blue: 'border-blue-100 dark:border-blue-900/30',
    gray: 'border-gray-100 dark:border-gray-800',
  };
  const iconColorMap: Record<string, string> = {
    indigo: 'text-indigo-600 dark:text-indigo-400',
    violet: 'text-violet-600 dark:text-violet-400',
    emerald: 'text-emerald-600 dark:text-emerald-400',
    amber: 'text-amber-600 dark:text-amber-400',
    blue: 'text-blue-600 dark:text-blue-400',
    gray: 'text-gray-500 dark:text-gray-400',
  };

  return (
    <div className={`rounded-xl border ${colorMap[color] || colorMap.gray} bg-white dark:bg-gray-900 p-5`}>
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white mb-4">
        <Icon size={16} className={iconColorMap[color] || iconColorMap.gray} />
        {title}
      </div>
      {children}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900 dark:text-white capitalize">{value}</span>
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const color = value >= 80 ? 'bg-emerald-500' : value >= 60 ? 'bg-indigo-500' : value >= 40 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{label}</span>
        <span className="font-semibold">{Math.round(value)}</span>
      </div>
      <div className="w-full h-2 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function renderEntityGroup(label: string, items: string[]) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <span className="text-xs text-gray-500 uppercase tracking-wider font-medium block mb-1">{label}</span>
      <div className="flex flex-wrap gap-1">
        {items.map((item, i) => (
          <span key={i} className="px-2 py-0.5 rounded-md text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

function hasEntities(entities: any): boolean {
  return Object.values(entities).some((arr: any) => Array.isArray(arr) && arr.length > 0);
}
