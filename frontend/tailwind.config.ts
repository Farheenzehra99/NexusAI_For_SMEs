import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          800: "#1e2a3a",
          900: "#0f172a",
          950: "#080e1a",
        },
        accent: {
          emerald: "#10b981",
          gold: "#f59e0b",
          blue: "#3b82f6",
          purple: "#8b5cf6",
          rose: "#f43f5e",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
