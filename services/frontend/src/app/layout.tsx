import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

// next/font downloads Inter at build time and serves it from our own origin, so
// there is no runtime request to a font CDN. Loading it here is what makes the
// brand face actually render: "Inter" previously sat fourth in the CSS font
// stack, behind ui-sans-serif and -apple-system, so it never won.
const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  // Open Graph and Twitter card URLs must be absolute. Next resolves
  // app/opengraph-image.png against this; without it the tags are emitted
  // relative and most crawlers drop the preview image.
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: "OpenGrow Studio",
  description: "AI content growth engine",
};

export const viewport: Viewport = {
  // Tints mobile browser chrome to the brand primary.
  themeColor: "#0b3b2e",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
