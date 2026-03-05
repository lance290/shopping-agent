import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: "#FDFBF7",
          dark: "#F5F0E8",
        },
        onyx: {
          DEFAULT: "#1B2A4A",
          muted: "#6B7B99",
        },
        ink: {
          DEFAULT: "#1B2A4A",
          muted: "#8090AB",
        },
        warm: {
          grey: "#D4CFC6",
          light: "#F9F6F0",
        },
        agent: {
          blurple: "#1B2A4A",
          camel: "#C5A46D",
        },
        navy: {
          DEFAULT: "#1B2A4A",
          light: "#2D4166",
          dark: "#0F1B33",
        },
        gold: {
          DEFAULT: "#C5A46D",
          light: "#DCC9A3",
          dark: "#A88B55",
        },
        status: {
          success: "#2D8A56",
          error: "#C53030",
        },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "SF Pro Text",
          "SF Pro Display",
          "Helvetica Neue",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
        serif: [
          "-apple-system",
          "BlinkMacSystemFont",
          "SF Pro Display",
          "Helvetica Neue",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic":
          "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
        "ai-glow": "linear-gradient(135deg, #1B2A4A 0%, #C5A46D 100%)",
      },
    },
  },
  plugins: [],
};
export default config;
