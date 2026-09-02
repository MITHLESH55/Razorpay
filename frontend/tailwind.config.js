/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        fintech: {
          bg: '#F4F6F8',
          card: '#FFFFFF',
          surface: '#F8FAFC',
          border: '#D9DEE7',
          borderLight: '#E8ECF2',
          textPrimary: '#172033',
          textSecondary: '#667085',
          textMuted: '#98A2B3',
          navy: '#183B67',
          navyDark: '#0F2642',
          blue: '#2563A6',
          blueHover: '#1D4ED8',
          blueLight: '#EFF6FF',
          accent: '#3B82C4',
        },
        semantic: {
          green: '#15803D',
          greenBg: '#F0FDF4',
          greenBorder: '#BBF7D0',
          amber: '#B7791F',
          amberBg: '#FEF3C7',
          amberBorder: '#FDE68A',
          red: '#C53030',
          redBg: '#FEF2F2',
          redBorder: '#FECACA',
          blue: '#2563A6',
          blueBg: '#EFF6FF',
          blueBorder: '#BFDBFE',
          neutral: '#1F2937',
          neutralBg: '#F3F4F6',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(16, 24, 40, 0.05), 0 1px 2px -1px rgba(16, 24, 40, 0.04)',
        'card-hover': '0 4px 12px 0 rgba(16, 24, 40, 0.08), 0 2px 4px -2px rgba(16, 24, 40, 0.04)',
        'dropdown': '0 10px 15px -3px rgba(16, 24, 40, 0.1), 0 4px 6px -4px rgba(16, 24, 40, 0.05)',
        'modal': '0 20px 25px -5px rgba(16, 24, 40, 0.15), 0 8px 10px -6px rgba(16, 24, 40, 0.08)',
      }
    },
  },
  plugins: [],
}
