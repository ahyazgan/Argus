import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        argus: {
          bg: "#0b1120",
          panel: "#111c34",
          accent: "#0ea5e9",
        },
      },
    },
  },
  plugins: [],
};

export default config;
