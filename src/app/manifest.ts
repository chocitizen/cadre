import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "CADRE Command",
    short_name: "CADRE",
    description: "Private sovereign intelligence and execution platform.",
    start_url: "/app",
    display: "standalone",
    background_color: "oklch(0.1 0 0)",
    theme_color: "oklch(0.145 0.008 230)",
    orientation: "any",
    icons: [
      {
        src: "/cadre-mark.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "maskable"
      }
    ]
  };
}
