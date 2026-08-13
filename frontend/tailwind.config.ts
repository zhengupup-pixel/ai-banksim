import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17212b",
        bank: "#0f766e",
        mint: "#dff7ef",
        gold: "#b7791f",
        paper: "#f5f8f6"
      },
      boxShadow: {
        panel: "0 14px 40px rgba(23, 33, 43, 0.055)"
      },
      borderRadius: {
        panel: "1.25rem"
      }
    }
  },
  plugins: []
} satisfies Config;
