/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Arial', 'Helvetica', 'sans-serif'],
        body: ['Arial', 'Helvetica', 'sans-serif'],
        mono: ['Arial', 'Helvetica', 'sans-serif'],
      },
      colors: {
        primary: { DEFAULT: '#1B4F8A', light: '#2E6DB4', dark: '#0F2D4F' },
        surface: '#FFFFFF',
        canvas: '#F0F4F8',
        border: '#E2E8F0',
        muted: '#718096',
      },
      animation: {
        'fade-up': 'fadeUp 0.4s ease both',
        'fade-in': 'fadeIn 0.3s ease both',
        'slide-in': 'slideIn 0.35s ease both',
      },
      keyframes: {
        fadeUp: { '0%': { opacity: 0, transform: 'translateY(14px)' }, '100%': { opacity: 1, transform: 'translateY(0)' } },
        fadeIn: { '0%': { opacity: 0 }, '100%': { opacity: 1 } },
        slideIn: { '0%': { opacity: 0, transform: 'translateX(-14px)' }, '100%': { opacity: 1, transform: 'translateX(0)' } },
      },
    },
  },
  plugins: [],
}
