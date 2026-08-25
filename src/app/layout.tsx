import type { Metadata, Viewport } from "next";
import { PwaRegistrar } from "@/components/pwa-registrar";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "CADRE Command",
    template: "%s · CADRE"
  },
  description: "Private sovereign intelligence and execution platform.",
  applicationName: "CADRE",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: "/cadre-mark.svg",
    apple: "/cadre-mark.svg"
  },
  robots: {
    index: false,
    follow: false,
    noarchive: true,
    nocache: true
  }
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  colorScheme: "dark",
  themeColor: "oklch(0.145 0.008 230)"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        {children}
        <PwaRegistrar />
      </body>
    </html>
  );
}
