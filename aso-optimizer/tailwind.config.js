/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './index.html',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"SF Pro Display"', '"SF Pro Text"', '"Helvetica Neue"', 'Arial', 'sans-serif'],
      },
      colors: {
        apple: {
          blue:      '#0071e3',
          blueDark:  '#0077ed',
          gray:      '#6e6e73',
          lightGray: '#f5f5f7',
          border:    '#d2d2d7',
          text:      '#1d1d1f',
        },
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        'card':       '0 2px 20px rgba(0,0,0,.08)',
        'card-hover': '0 8px 30px rgba(0,0,0,.12)',
      },
    },
  },
  plugins: [],
};
