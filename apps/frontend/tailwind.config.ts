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
          DEFAULT: "#F5F5F7",
          dark: "#1D1D1F",
        },
        onyx: {
          DEFAULT: "#1D1D1F",
          muted: "#6E6E73",
        },
        warm: {
          grey: "#E5E5EA",
          light: "#FAFAFB",
        },
        agent: {
          blurple: "#0071E3",
          camel: "#73C3E6",
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
        "ai-glow": "linear-gradient(135deg, #0071E3 0%, #73C3E6 100%)",
      },
    },
  },
  plugins: [],
};
export default config;
