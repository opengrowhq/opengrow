import type { MetadataRoute } from "next";

// Served at /manifest.webmanifest. Next links it from <head> automatically.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "OpenGrow Studio",
    short_name: "OpenGrow",
    description: "AI content growth engine",
    start_url: "/",
    display: "standalone",
    // Canvas, so the splash screen matches the app shell rather than flashing
    // a colour that appears nowhere in the product.
    background_color: "#f5f7fa",
    theme_color: "#0b3b2e",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        // Full-bleed plate with the mark at 58% of the canvas, so it survives
        // the ~80% circular crop Android applies to maskable icons.
        purpose: "maskable",
      },
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
