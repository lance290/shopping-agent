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
          DEFAULT: "#FFFFFF",
          dark: "#F5F5F5",
        },
        onyx: {
          DEFAULT: "#0F1111",
          muted: "#565959",
        },
        ink: {
          DEFAULT: "#0F1111",
          muted: "#565959",
        },
        warm: {
          grey: "#D5D9D9",
          light: "#F7F8F8",
        },
        agent: {
          blurple: "#131A22",
          camel: "#FF9900",
        },
        navy: {
          DEFAULT: "#131A22",
          light: "#232F3E",
          dark: "#0A0E14",
        },
        gold: {
          DEFAULT: "#FF9900",
          light: "#FFB84D",
          dark: "#E68A00",
        },
        accent: {
          blue: "#0066C0",
          "blue-hover": "#004F9A",
        },
        status: {
          success: "#067D62",
          error: "#CC0C39",
        },
        deal: {
          red: "#CC0C39",
          badge: "#067D62",
        },
        border: {
          DEFAULT: "#D5D9D9",
          hover: "#A6ACAF",
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
        "ai-glow": "linear-gradient(135deg, #131A22 0%, #FF9900 100%)",
      },
    },
  },
  plugins: [],
};
export default config;
