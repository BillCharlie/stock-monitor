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
      fontSize: {
        // Base is now 15px; override xs/sm so they stay readable
        'xs':   ['0.8rem',  { lineHeight: '1.2rem'  }],  // 12px  (was 9.75px)
        'sm':   ['0.9rem',  { lineHeight: '1.35rem' }],  // 13.5px (was 11.375px)
        'base': ['1rem',    { lineHeight: '1.6rem'  }],  // 15px
        'lg':   ['1.1rem',  { lineHeight: '1.7rem'  }],  // 16.5px
        'xl':   ['1.2rem',  { lineHeight: '1.8rem'  }],  // 18px
        '2xl':  ['1.4rem',  { lineHeight: '2rem'    }],  // 21px
      },
    },
  },
  plugins: [],
}
