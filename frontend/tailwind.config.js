export default {
    content: ["./index.html", "./src/**/*.{ts,tsx}"],
    theme: {
        extend: {
            colors: {
                ink: "#0B0E0D", // Deep near-black background
                mist: "#F4EFE6", // Warm neutral for highlights
                night: "#121614", // Secondary dark surface
                glass: "rgba(255, 255, 255, 0.025)", // Quiet surface tint
                ember: "#789A80", // Restrained analysis accent
                pine: "#405C47", // Complementary dark green
                slate: "#9A9E9B", // Neutral gray
                cream: "#EADFCE", // Warm secondary
                input: "#161A18", // Dark gray for input boxes
                loading: "#C58A5B", // Orange for loading
                warning: "#D97878", // Red for warning
                "terminal-green": "#8FB996",
                "terminal-amber": "#D1A56D",
                "terminal-red": "#D97878"
            },
            fontFamily: {
                sans: ["IBM Plex Sans", "ui-sans-serif", "system-ui"],
                mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"]
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
};
