import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class', // Keeping for compatibility but default is light
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#F7F9FA',
          secondary: '#FFFFFF',
          tertiary: '#F1F5F9',
        },
        foreground: {
          DEFAULT: '#1F2937',
          secondary: '#6B7280',
          muted: '#9CA3AF',
        },
        primary: {
          DEFAULT: '#00D09C',
          50: '#E6F9F3',
          100: '#CCF3E7',
          200: '#99E7CF',
          300: '#66DBB7',
          400: '#33CF9F',
          500: '#00D09C',
          600: '#00B386',
          700: '#009670',
          800: '#00795A',
          900: '#005C44',
        },
        accent: {
          DEFAULT: '#00D09C',
          green: '#00D09C',
          blue: '#3B82F6',
          teal: '#14B8A6',
        },
        success: '#10B981',
        warning: '#F59E0B',
        error: '#EF4444',
        info: '#3B82F6',
        border: {
          DEFAULT: '#E5E7EB',
          light: '#F3F4F6',
        },
        ring: '#00D09C',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'typing': 'typing 1.5s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        typing: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.03)',
        'card-hover': '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
        'subtle': '0 1px 2px rgba(0, 0, 0, 0.04)',
      },
    },
  },
  plugins: [],
};

export default config;
