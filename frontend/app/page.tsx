import Link from "next/link";

export default function Home() {
  return (
    <main style={{ maxWidth: 640, margin: "4rem auto", padding: "0 1rem" }}>
      <h1>Lumen</h1>
      <p>
        Check suspicious images, audio, video, links, or WhatsApp forwards for
        signs of AI generation or manipulation — before you trust or share them.
      </p>
      <p>
        <Link href="/analyze">Analyze media →</Link>
      </p>
    </main>
  );
}
