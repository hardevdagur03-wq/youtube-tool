import { useState, useEffect } from 'react';
import { Menu, X, Github, Moon, Sun } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
  }, [dark]);

  const links = [
    { label: 'Home', href: '#hero' },
    { label: 'Export Tool', href: '#export-form', bold: true },
    { label: 'Documentation', href: '#how-it-works' },
  ];

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-white/90 backdrop-blur-xl border-b border-gray-100 shadow-sm'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 lg:h-[72px]">
          <a href="#hero" className="flex items-center gap-2.5 no-underline">
            <img src="/static/logo.png" alt="Matrix Academy" className="h-8 w-auto rounded-lg" />
            <span className={`font-bold text-lg ${scrolled ? 'text-gray-900' : 'text-white'}`}>
              YouTube Export
            </span>
          </a>

          <nav className="hidden md:flex items-center gap-1">
            {links.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-all-200 no-underline ${
                  link.bold
                    ? scrolled
                      ? 'text-emerald-600 bg-emerald-50'
                      : 'text-emerald-300 bg-white/10'
                    : scrolled
                      ? 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                      : 'text-white/80 hover:text-white hover:bg-white/10'
                }`}
              >
                {link.label}
              </a>
            ))}
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className={`p-2 rounded-lg transition-all-200 ${
                scrolled ? 'text-gray-500 hover:text-gray-900 hover:bg-gray-100' : 'text-white/70 hover:text-white hover:bg-white/10'
              }`}
              aria-label="GitHub"
            >
              <Github size={18} />
            </a>
            <button
              onClick={() => setDark(!dark)}
              className={`p-2 rounded-lg transition-all-200 ${
                scrolled ? 'text-gray-500 hover:text-gray-900 hover:bg-gray-100' : 'text-white/70 hover:text-white hover:bg-white/10'
              }`}
              aria-label="Toggle dark mode"
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </nav>

          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className={`md:hidden p-2 rounded-lg transition-all-200 ${
              scrolled ? 'text-gray-600' : 'text-white'
            }`}
            aria-label="Toggle menu"
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden border-t border-gray-100 bg-white shadow-lg overflow-hidden"
          >
            <div className="px-4 py-4 space-y-1">
              {links.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  className={`block px-3 py-2.5 rounded-lg text-sm font-medium no-underline ${
                    link.bold ? 'text-emerald-600 bg-emerald-50' : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {link.label}
                </a>
              ))}
              <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-gray-700 hover:bg-gray-100 no-underline">
                <Github size={16} /> GitHub
              </a>
              <button onClick={() => { setDark(!dark); setMenuOpen(false); }} className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-gray-700 hover:bg-gray-100 w-full">
                {dark ? <Sun size={16} /> : <Moon size={16} />} {dark ? 'Light Mode' : 'Dark Mode'}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
