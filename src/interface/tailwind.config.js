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
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'
      },
      colors: {
        background: {
          DEFAULT: '#181818',      // Main background
          secondary: '#252526',    // Secondary background
          tertiary: '#2a2d2e',    // Tertiary/hover background
          selected: '#37373d'      // Selected item background
        },
        border: {
          DEFAULT: '#333333',      // Default borders
          active: '#454545',       // Active/hover borders
          highlight: '#007fd4'     // Highlighted borders
        },
        text: {
          DEFAULT: '#cccccc',      // Primary text
          secondary: '#808080',    // Secondary text
          inactive: '#6e7681',     // Inactive text
          white: '#ffffff',        // Pure white text
          link: '#3794ff'          // Link text
        },
        accent: {
          blue: '#007fd4',         // Primary blue
          green: '#4ec9b0',        // Success green
          red: '#f44747',          // Error red
          yellow: '#e9d16c',       // Warning yellow
          purple: '#c586c0'        // Special purple
        },
        editor: {
          background: '#1e1e1e',   // Code editor background
          lineHighlight: '#2f3337', // Current line highlight
          selection: '#264f78',    // Selection background
          widget: '#252526'        // Widget background
        },
        scrollbar: {
          thumb: '#424242',        // Scrollbar thumb
          hover: '#4f4f4f'         // Scrollbar hover
        }
      },
      fontSize: {
        code: '13px',             // Code font size
        ui: '13px'                // UI font size
      },
      spacing: {
        tree: '0.5rem'            // Tree indent spacing
      },
      boxShadow: {
        'selected': '0 0 0 1px rgba(255, 255, 255, 0.05)',
      },
      opacity: {
        'dim': '0.8'
      }
    }
  },
  plugins: [require("tailwindcss-animate")]
}