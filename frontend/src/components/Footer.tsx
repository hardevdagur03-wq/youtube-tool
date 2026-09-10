import { Github, FileText, Code2, Mail } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-gray-100 bg-[#F8FAFC]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div className="col-span-2 md:col-span-1">
            <a href="#hero" className="flex items-center gap-2 mb-3 no-underline">
              <img src="/static/logo.png" alt="Matrix Academy" className="h-7 w-auto rounded-md" />
              <span className="font-bold text-gray-900 text-sm">YouTube Export</span>
            </a>
            <p className="text-sm text-gray-500 leading-relaxed max-w-xs">
              Export all uploaded public videos from any YouTube channel to CSV format. Built with the YouTube Data API v3.
            </p>
          </div>

          {[
            { title: 'Product', links: [{ label: 'Channel Export', href: '#export-form' }, { label: 'CSV Download', href: '#export-form' }, { label: 'API', href: '#how-it-works' }] },
            { title: 'Resources', links: [{ label: 'Documentation', href: '#how-it-works', icon: FileText }, { label: 'YouTube API v3', href: 'https://developers.google.com/youtube/v3', icon: Code2, external: true }, { label: 'GitHub', href: 'https://github.com', icon: Github, external: true }] },
            { title: 'Company', links: [{ label: 'About', href: '#' }, { label: 'Contact', href: '#', icon: Mail }, { label: 'Version 1.0.0' }] },
          ].map((col) => (
            <div key={col.title}>
              <h4 className="text-xs font-semibold text-gray-900 uppercase tracking-wider mb-4">{col.title}</h4>
              <ul className="space-y-2.5">
                {col.links.map((link) => {
                  const Icon = (link as any).icon;
                  const isExternal = (link as any).external;
                  const Tag = link.href ? 'a' : 'span';
                  const props: any = link.href ? { href: link.href, ...(isExternal ? { target: '_blank', rel: 'noopener noreferrer' } : {}) } : {};
                  return (
                    <li key={link.label}>
                      <Tag {...props} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-emerald-600 transition-colors no-underline">
                        {Icon && <Icon size={14} />}
                        {link.label}
                      </Tag>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </div>
      <div className="border-t border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col sm:flex-row justify-between items-center gap-2">
          <p className="text-xs text-gray-400">&copy; 2026 YouTube CSV Export Tool</p>
          <p className="text-xs text-gray-400">Powered by the YouTube Data API v3</p>
        </div>
      </div>
    </footer>
  );
}
