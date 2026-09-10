import { Link } from 'react-router-dom';
import { ArrowRight, CheckCircle2, type LucideIcon } from 'lucide-react';

interface WorkflowCardProps {
  icon: LucideIcon;
  badge: string;
  title: string;
  description: string;
  features: string[];
  cta: string;
  to: string;
  accentColor: 'emerald' | 'teal' | 'violet';
}

const colorStyles = {
  emerald: {
    iconBg: 'bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400',
    badge: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/70 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800/60',
    btn: 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-600/20',
    check: 'text-emerald-500',
    borderHover: 'hover:border-emerald-500/50 dark:hover:border-emerald-500/40',
  },
  teal: {
    iconBg: 'bg-teal-500/10 dark:bg-teal-500/20 text-teal-600 dark:text-teal-400',
    badge: 'bg-teal-50 text-teal-700 dark:bg-teal-950/70 dark:text-teal-300 border-teal-200 dark:border-teal-800/60',
    btn: 'bg-teal-600 hover:bg-teal-700 text-white shadow-teal-600/20',
    check: 'text-teal-500',
    borderHover: 'hover:border-teal-500/50 dark:hover:border-teal-500/40',
  },
  violet: {
    iconBg: 'bg-violet-500/10 dark:bg-violet-500/20 text-violet-600 dark:text-violet-400',
    badge: 'bg-violet-50 text-violet-700 dark:bg-violet-950/70 dark:text-violet-300 border-violet-200 dark:border-violet-800/60',
    btn: 'bg-violet-600 hover:bg-violet-700 text-white shadow-violet-600/20',
    check: 'text-violet-500',
    borderHover: 'hover:border-violet-500/50 dark:hover:border-violet-500/40',
  },
};

export default function WorkflowCard({
  icon: Icon,
  badge,
  title,
  description,
  features,
  cta,
  to,
  accentColor,
}: WorkflowCardProps) {
  const styles = colorStyles[accentColor];

  return (
    <Link
      to={to}
      className="group relative flex flex-col h-full no-underline"
    >
      <div
        className={`relative flex flex-col justify-between h-full bg-white dark:bg-gray-900 rounded-2xl border border-gray-200/90 dark:border-gray-800 p-6 sm:p-7 shadow-sm hover:shadow-xl ${styles.borderHover} transition-all duration-300 overflow-hidden`}
      >
        {/* Subtle hover gradient background */}
        <div className="absolute inset-0 bg-gradient-to-b from-gray-50/50 to-transparent dark:from-gray-800/20 dark:to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

        {/* Top Header & Content */}
        <div className="relative z-10 flex-1 flex flex-col">
          {/* Header Row: Icon & Tag */}
          <div className="flex items-center justify-between gap-3 mb-5">
            <div
              className={`w-12 h-12 rounded-xl ${styles.iconBg} flex items-center justify-center group-hover:scale-110 transition-transform duration-200`}
            >
              <Icon size={24} strokeWidth={2} />
            </div>
            <span
              className={`text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border ${styles.badge}`}
            >
              {badge}
            </span>
          </div>

          {/* Title */}
          <h3 className="text-xl font-bold text-gray-900 dark:text-white tracking-tight mb-2 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
            {title}
          </h3>

          {/* Short Description */}
          <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed mb-6">
            {description}
          </p>

          {/* Feature Capabilities Checklist */}
          <div className="mt-auto pt-2 border-t border-gray-100 dark:border-gray-800/80">
            <ul className="space-y-2 py-3">
              {features.map((feature) => (
                <li
                  key={feature}
                  className="flex items-center gap-2 text-xs font-medium text-gray-600 dark:text-gray-300"
                >
                  <CheckCircle2 size={14} className={`flex-shrink-0 ${styles.check}`} />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom CTA Button */}
        <div className="relative z-10 mt-5 pt-4 border-t border-gray-100 dark:border-gray-800/80">
          <div
            className={`w-full py-2.5 px-4 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 ${styles.btn} shadow-md transition-all duration-200`}
          >
            <span>{cta}</span>
            <ArrowRight size={15} className="group-hover:translate-x-1 transition-transform duration-200" />
          </div>
        </div>
      </div>
    </Link>
  );
}
