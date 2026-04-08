/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './index.html',
    './list/**/*.html',
    './trending/**/*.html',
    './clients/**/*.html',
    './store/**/*.html',
    './webhook/**/*.html',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"SF Pro Display"', '"Segoe UI"', 'Roboto', 'sans-serif'],
      },
      colors: {
        surface: {
          DEFAULT: '#111114',
          card:    '#1c1c1e',
          hover:   '#2c2c2e',
          border:  '#3a3a3c',
        },
        accent: {
          blue:   '#0a84ff',
          purple: '#bf5af2',
          green:  '#30d158',
          orange: '#ff9f0a',
        },
      },
      backgroundImage: {
        'hero-gradient': 'radial-gradient(ellipse 80% 60% at 50% -10%, rgba(10,132,255,0.18) 0%, transparent 70%)',
        'card-shine':    'linear-gradient(135deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0) 60%)',
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.6), 0 8px 24px rgba(0,0,0,0.4)',
        glow: '0 0 32px rgba(10,132,255,0.25)',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease both',
      },
      keyframes: {
        fadeIn: { from: { opacity: '0', transform: 'translateY(12px)' }, to: { opacity: '1', transform: 'none' } },
      },
    },
  },
  plugins: [],
};
