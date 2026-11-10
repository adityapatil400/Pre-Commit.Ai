/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: '#050505',
          muted: '#555555',
          subtle: '#888888',
          border: '#202020',
          'border-light': '#E5E7EB',
          divider: '#A0A0A0',
          focus: '#278BEA',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        'panel': '18px',
        'control': '14px',
      },
      backgroundImage: {
        'hero-gradient': "radial-gradient(ellipse at 72% 12%, rgba(177, 155, 255, 0.28), transparent 35%), radial-gradient(ellipse at 72% 42%, rgba(45, 174, 255, 0.30), transparent 42%), #ffffff",
      },
    },
  },
  plugins: [],
}

