import { motion } from 'framer-motion';
import {
  Clock,
  Eye,
  ThumbsUp,
  MessageCircle,
  Calendar,
  Tag,
  Globe,
  Lock,
  CheckCircle2,
  XCircle,
  Copy,
  ChevronDown,
  ChevronUp,
  Youtube,
  ExternalLink,
} from 'lucide-react';
import { useState } from 'react';
import { Card, Badge, Container } from '../ui';
import type { VideoMetadata } from '../../types';

interface VideoDetailsProps {
  metadata: VideoMetadata;
}

function StatItem({ icon: Icon, label, value }: { icon: any; label: string; value: string | number | null }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800">
      <div className="w-9 h-9 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
        <Icon size={15} className="text-gray-500 dark:text-gray-400" />
      </div>
      <div>
        <div className="text-sm font-semibold text-gray-900 dark:text-white">{value ?? '—'}</div>
        <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
      </div>
    </div>
  );
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all-200"
      title={`Copy ${label}`}
    >
      <Copy size={12} />
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}

function DetailRow({ label, value, copyValue }: { label: string; value: string | null; copyValue?: string }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <span className="text-sm text-gray-500 dark:text-gray-400">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-gray-900 dark:text-white text-right max-w-[200px] truncate">
          {value ?? '—'}
        </span>
        {copyValue && <CopyButton text={copyValue} label={label} />}
      </div>
    </div>
  );
}

function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-gray-200 dark:bg-gray-700 rounded-lg ${className}`} />
  );
}

export function VideoDetailsSkeleton() {
  return (
    <Container>
      <div className="max-w-4xl mx-auto space-y-6">
        <Skeleton className="h-64 w-full rounded-2xl" />
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20" />)}
        </div>
        <Skeleton className="h-32" />
      </div>
    </Container>
  );
}

export default function VideoDetails({ metadata }: VideoDetailsProps) {
  const [descExpanded, setDescExpanded] = useState(false);
  const v = metadata;
  const bestThumb = v.thumbnails.maxres || v.thumbnails.high || v.thumbnails.medium || v.thumbnails.default;

  const statusBadge = () => {
    const status = v.privacy || v.live_status || 'public';
    const map: Record<string, { label: string; variant: 'success' | 'warning' | 'error' | 'info' }> = {
      public: { label: 'Public', variant: 'success' },
      private: { label: 'Private', variant: 'error' },
      unlisted: { label: 'Unlisted', variant: 'warning' },
      upcoming: { label: 'Upcoming', variant: 'info' },
      live: { label: 'Live', variant: 'error' },
      none: { label: 'Public', variant: 'success' },
    };
    const m = map[status] || { label: status, variant: 'info' as const };
    return <Badge variant={m.variant}>{m.label}</Badge>;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <Container>
        <div className="max-w-4xl mx-auto space-y-6 pb-12">

          {/* Thumbnail */}
          {bestThumb && (
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="relative overflow-hidden rounded-2xl bg-gray-100 dark:bg-gray-800 shadow-elevated group"
            >
              <img
                src={bestThumb}
                alt={v.title || 'Video thumbnail'}
                className="w-full aspect-video object-cover group-hover:scale-[1.02] transition-all-300"
              />
              {v.duration.compact && (
                <div className="absolute bottom-3 right-3 px-2.5 py-1 rounded-lg bg-black/70 text-white text-xs font-semibold backdrop-blur-sm">
                  {v.duration.compact}
                </div>
              )}
            </motion.div>
          )}

          {/* Title + Channel */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.2 }}
          >
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  {statusBadge()}
                  {v.caption && <Badge variant="info">CC</Badge>}
                  {v.embeddable && <Badge variant="success">Embeddable</Badge>}
                </div>
                <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white leading-tight mb-2">
                  {v.title || 'Untitled Video'}
                </h2>
                <div className="flex items-center gap-3 flex-wrap">
                  {v.channel.name && (
                    <a
                      href={v.channel.url || '#'}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors no-underline"
                    >
                      <Youtube size={14} />
                      {v.channel.name}
                      {v.channel.verified && (
                        <CheckCircle2 size={12} className="text-emerald-500" />
                      )}
                    </a>
                  )}
                  {v.published_at.relative && (
                    <span className="text-sm text-gray-400 dark:text-gray-500">
                      {v.published_at.relative}
                    </span>
                  )}
                </div>
              </div>
              <CopyButton text={v.video_id} label="Video ID" />
            </div>
          </motion.div>

          {/* Statistics Grid */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.3 }}
            className="grid grid-cols-2 sm:grid-cols-4 gap-3"
          >
            <StatItem icon={Eye} label="Views" value={v.statistics.views_formatted} />
            <StatItem icon={ThumbsUp} label="Likes" value={v.statistics.likes_formatted} />
            <StatItem icon={MessageCircle} label="Comments" value={v.statistics.comments_formatted} />
            <StatItem icon={Clock} label="Duration" value={v.duration.readable || v.duration.compact} />
          </motion.div>

          {/* Description Card */}
          {v.description.full && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.35 }}
            >
              <Card padding="md">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Description</h3>
                  {v.description.full.length > 300 && (
                    <button
                      onClick={() => setDescExpanded(!descExpanded)}
                      className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                    >
                      {descExpanded ? 'Show less' : 'Show more'}
                      {descExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    </button>
                  )}
                </div>
                <p className={`text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap leading-relaxed ${!descExpanded ? 'line-clamp-4' : ''}`}>
                  {v.description.full}
                </p>
                {v.description.hashtags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {v.description.hashtags.map((tag) => (
                      <span key={tag} className="px-2 py-0.5 rounded-full bg-violet-50 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400 text-xs font-medium">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </Card>
            </motion.div>
          )}

          {/* Video Information Card */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.4 }}
          >
            <Card padding="md">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">Video Information</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">Technical details and metadata</p>
              <div className="divide-y divide-gray-100 dark:divide-gray-800">
                <DetailRow label="Video ID" value={v.video_id} copyValue={v.video_id} />
                <DetailRow label="Published" value={v.published_at.localized} />
                <DetailRow label="Duration" value={v.duration.readable || v.duration.compact} />
                <DetailRow label="Privacy" value={v.privacy || 'Public'} />
                {v.live_status && <DetailRow label="Live Status" value={v.live_status} />}
                {v.category_id && <DetailRow label="Category ID" value={v.category_id} />}
                {v.language && <DetailRow label="Language" value={v.language} />}
                {v.default_audio_language && (
                  <DetailRow label="Audio Language" value={v.default_audio_language} />
                )}
                <DetailRow label="License" value={v.license || 'Standard'} />
                <DetailRow label="Captions" value={v.caption ? 'Available' : 'None'} />
                <DetailRow label="Embeddable" value={v.embeddable ? 'Yes' : 'No'} />
              </div>
            </Card>
          </motion.div>

          {/* Tags */}
          {v.tags.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.45 }}
            >
              <Card padding="md">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Tags</h3>
                <div className="flex flex-wrap gap-1.5">
                  {v.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2.5 py-1 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 text-xs font-medium"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </Card>
            </motion.div>
          )}

          {/* Actions */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.5 }}
            className="flex flex-wrap gap-3"
          >
            <a
              href={`https://www.youtube.com/watch?v=${v.video_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-semibold text-sm hover:bg-gray-200 dark:hover:bg-gray-700 transition-all-200 no-underline"
            >
              <ExternalLink size={15} />
              Watch on YouTube
            </a>
          </motion.div>

        </div>
      </Container>
    </motion.div>
  );
}
