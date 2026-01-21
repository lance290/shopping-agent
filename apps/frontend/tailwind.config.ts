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
          DEFAULT: "#202124",
          dark: "#171717",
        },
        onyx: {
          DEFAULT: "#E8EAED",
          muted: "#9AA0A6",
        },
        ink: {
          DEFAULT: "#202124",
          muted: "#5F6368",
        },
        warm: {
          grey: "#3C4043",
          light: "#2B2F33",
        },
        agent: {
          blurple: "#1A73E8",
          camel: "#8AB4F8",
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
        "ai-glow": "linear-gradient(135deg, #1A73E8 0%, #8AB4F8 100%)",
      },
    },
  },
  plugins: [],
};
export default config;
