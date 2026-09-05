import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Lumen — check suspicious media before you share it",
  description:
    "Submit an image, audio clip, video, link, or WhatsApp forward. Lumen fuses five independent signals and explains the verdict in plain language.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0 }}>{children}</body>
    </html>
  );
}
