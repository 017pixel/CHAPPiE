import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0D0D0D", // Deep near-black background
        mist: "#F4EFE6", // Warm neutral for highlights
        night: "#121212", // Secondary dark surface
        glass: "rgba(255, 255, 255, 0.03)", // Glassmorphism base
        ember: "#6A8D73", // NEW: Dark Pastel Green accent (replacing orange)
        pine: "#3D5A44", // Complementary dark green
        slate: "#8C8C8C", // Neutral gray
        cream: "#EADFCE", // Warm secondary
        input: "#1A1A1A", // NEW: Dark gray for input boxes
        loading: "#F26A1B", // Orange for loading
        warning: "#EF4444" // Red for warning
      },
      fontFamily: {
        sans: ["Space Grotesk", "ui-sans-serif", "system-ui"]
      },
      borderRadius: {
        "squircle-sm": "1rem",
        "squircle-md": "1.5rem",
        "squircle-lg": "2rem",
        "squircle-xl": "3rem"
      },
      boxShadow: {
        panel: "0 20px 60px rgba(0, 0, 0, 0.5)",
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.3)"
      }
    }
  },
  plugins: []
} satisfies Config;
