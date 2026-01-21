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
          DEFAULT: "#FAFAFA",
          dark: "#0A0A0A",
        },
        onyx: {
          DEFAULT: "#1A1A1A",
          muted: "#404040",
        },
        warm: {
          grey: "#E5E5E5",
          light: "#F5F5F5",
        },
        agent: {
          blurple: "#6366F1",
          camel: "#D4B483",
        },
        status: {
          success: "#10B981",
          error: "#F43F5E",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "sans-serif"],
        serif: ["var(--font-playfair)", "serif"],
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic":
          "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
        "ai-glow": "linear-gradient(135deg, #6366F1 0%, #D4B483 100%)",
      },
    },
  },
  plugins: [],
};
export default config;
