/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: { DEFAULT: 'var(--bg)', 2: 'var(--bg-2)', 3: 'var(--bg-3)', 4: 'var(--bg-4)', 5: 'var(--bg-5)' },
        border: { DEFAULT: 'var(--border)', 2: 'var(--border-2)' },
        accent: { DEFAULT: 'var(--accent)', 2: 'var(--accent-2)', glow: 'rgba(79,110,247,0.12)' },
        ink: { DEFAULT: 'var(--ink)', 2: 'var(--ink-2)', 3: 'var(--ink-3)' },
        success: 'var(--success)',
        warn: 'var(--warn)',
        danger: 'var(--danger)',
        info: '#06b6d4',
        pink: '#e879f9',
      },
      fontFamily: {
        sans: ['Outfit', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
