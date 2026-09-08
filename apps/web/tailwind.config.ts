import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f4f9",
          100: "#dbe5f1",
          200: "#b8cce3",
          300: "#89aed1",
          400: "#558bbe",
          500: "#346fa7",
          600: "#25578a",
          700: "#1e466f",
          800: "#1a3b5c",
          900: "#16314c",
          950: "#12233f",
          navy: "#12233F",
          gold: "#D9A94A",
          "gold-dark": "#96731F",
          cream: "#F4F1EA",
        },
      },
      fontFamily: {
        serif: ["Georgia", "Cambria", "'Times New Roman'", "Times", "serif"],
      },
    },
  },
  plugins: [],
};
export default config;
