/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      borderRadius: {
        'sm': '1px',
        DEFAULT: '1px',
        'md': '4px',
        'lg': '6px',
        'xl': '8px',
        '2xl': '10px',
      },
      fontSize: {
        code: '13px',
        ui: '13px'
      },
      spacing: {
        tree: '0.5rem'
      },
      opacity: {
        'dim': '0.8'
      }
    }
  },
  plugins: [require("tailwindcss-animate")]
}