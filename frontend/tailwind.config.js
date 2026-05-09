/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0D0D0D',
        panel: '#141414',
        border: '#2A2A2A',
        up: '#26A69A',
        down: '#EF5350',
      },
    },
  },
  plugins: [],
}
