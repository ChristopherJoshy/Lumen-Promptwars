import type { Metadata } from "next";
import { Inter, Playfair_Display, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans" });
const display = Playfair_Display({ subsets: ["latin"], style: ["italic", "normal"], variable: "--font-display" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: {
    default: "Lumen — check suspicious media before you share it",
    template: "%s · Lumen",
  },
  description:
    "Submit an image, audio clip, video, link, or WhatsApp forward. Lumen fuses five independent signals and explains the verdict in plain language.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${display.variable} ${mono.variable}`}>
      <body className="min-h-screen bg-paper text-ink antialiased">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-white focus:px-3 focus:py-2"
        >
          Skip to content
        </a>
        <SiteHeader />
        <div id="main">{children}</div>
        <SiteFooter />
      </body>
    </html>
  );
}
