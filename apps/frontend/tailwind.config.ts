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
          DEFAULT: "#DADDE0",
          dark: "#1C1E22",
        },
        onyx: {
          DEFAULT: "#1C1E22",
          muted: "#5F6670",
        },
        warm: {
          grey: "#C4C9CE",
          light: "#F0F2F4",
        },
        agent: {
          blurple: "#4E6D85",
          camel: "#88A1B4",
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
        "ai-glow": "linear-gradient(135deg, #4E6D85 0%, #88A1B4 100%)",
      },
    },
  },
  plugins: [],
};
export default config;
