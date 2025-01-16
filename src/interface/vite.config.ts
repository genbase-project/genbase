import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import svgr from 'vite-plugin-svgr' 

export default defineConfig({
  plugins: [react(),
    svgr({ 
      svgrOptions: {},
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
