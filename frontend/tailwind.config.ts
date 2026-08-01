import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'bonde-green': '#2e5339',
        'bonde-sage': '#4a7255',
        'bonde-oat': '#fbf8f3',
        'bonde-light': '#ebf3ed',
        'bonde-earth': '#8c6d46',
        'bonde-dark': '#1b3524',
      },
      fontFamily: {
        serif: ['Georgia', 'Cambria', '"Times New Roman"', 'Times', 'serif'],
        sans: ['system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        'soft': '0 4px 20px -2px rgba(0, 0, 0, 0.05)',
        'card': '0 10px 30px -4px rgba(0, 0, 0, 0.06)',
      },
    },
  },
  plugins: [],
}
export default config
