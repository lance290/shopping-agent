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
          DEFAULT: "#E1DDD6",
          dark: "#1F1B16",
        },
        onyx: {
          DEFAULT: "#211E1A",
          muted: "#6D625A",
        },
        warm: {
          grey: "#C8BFB2",
          light: "#F4F1EA",
        },
        agent: {
          blurple: "#B0744D",
          camel: "#D6B39A",
        },
        status: {
          success: "#34C759",
          error: "#FF3B30",
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
        "ai-glow": "linear-gradient(135deg, #B0744D 0%, #D6B39A 100%)",
      },
    },
  },
  plugins: [],
};
export default config;
