/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['SF Mono', 'Monaco', 'Consolas', 'monospace'],
      },
      colors: {
        emerald: {
          50: '#ECFDF5',
          100: '#D1FAE5',
          200: '#A7F3D0',
          300: '#6EE7B7',
          400: '#34D399',
          500: '#10B981',
          600: '#059669',
          700: '#047857',
          800: '#065F46',
          900: '#064E3B',
        },
      },
      fontSize: {
        'hero': ['56px', '1.1'],
        'section': ['36px', '1.2'],
      },
      spacing: {
        '18': '4.5rem',
      },
      borderRadius: {
        '2xl': '16px',
        '3xl': '20px',
      },
      boxShadow: {
        'glass': '0 0 0 1px rgba(255,255,255,0.1), 0 8px 32px rgba(0,0,0,0.06)',
        'card': '0 0 0 1px rgba(0,0,0,0.04), 0 2px 4px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.04)',
        'card-hover': '0 0 0 1px rgba(0,0,0,0.04), 0 8px 32px rgba(0,0,0,0.08)',
        'elevated': '0 0 0 1px rgba(0,0,0,0.04), 0 2px 4px rgba(0,0,0,0.02), 0 8px 24px rgba(0,0,0,0.04), 0 24px 48px rgba(0,0,0,0.06)',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        },
      },
    },
  },
  plugins: [],
}
