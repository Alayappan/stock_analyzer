/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        finance: {
          bg: '#0b0f19',
          card: '#111827',
          cardHover: '#172033',
          border: '#1f2937',
          borderLight: '#374151',
          accent: '#2563eb',
          accentHover: '#1d4ed8',
          success: '#10b981',
          successBg: 'rgba(16, 185, 129, 0.1)',
          danger: '#ef4444',
          dangerBg: 'rgba(239, 68, 68, 0.1)',
          warning: '#f59e0b',
          cyan: '#06b6d4',
          muted: '#9ca3af',
          lightText: '#f3f4f6'
        }
      },
      fontFamily: {
        mono: ['SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
