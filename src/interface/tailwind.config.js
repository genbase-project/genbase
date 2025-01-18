/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
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