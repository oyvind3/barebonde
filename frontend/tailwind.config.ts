import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'farm-green': '#2d5016',
        'farm-light': '#e8f4e8',
      },
    },
  },
  plugins: [],
}
export default config
