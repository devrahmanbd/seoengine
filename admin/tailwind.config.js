/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#6366F1',
        background: '#FAFAFA',
        surface: '#FFFFFF',
        textPrimary: '#0A0A0A',
        textSecondary: '#6B6B6B',
        border: '#E8E8EC',
        success: '#10B981',
        warning: '#F59E0B',
        error: '#EF4444',
      },
      fontFamily: {
        display: ['General Sans', 'system-ui', 'sans-serif'],
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      spacing: {
        1: '4px',
        2: '8px',
        3: '12px',
        4: '16px',
        5: '20px',
        6: '24px',
        8: '32px',
        10: '40px',
        12: '48px',
        16: '64px',
        20: '80px',
        24: '96px',
      },
      borderRadius: {
        tag: '4px',
        btn: '6px',
        card: '8px',
        modal: '12px',
      },
    },
  },
  plugins: [],
}