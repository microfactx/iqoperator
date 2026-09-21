import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0B0E14",
        surface: "#151A23",
        border: "#232A36",
        foreground: "#E6E6E6",
        muted: "#8A8F98",
        primary: { DEFAULT: "#0066FF", hover: "#0052CC" },
        success: "#3DD68C",
        destructive: "#FF5470",
        accent: "#00D1A0",
      },
      borderRadius: { lg: "10px" },
    },
  },
  plugins: [],
};
export default config;
