import Link from "next/link";
import {
  AudioLines,
  FileSearch,
  Fingerprint,
  History,
  Hourglass,
  MessageCircle,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { VerdictBadge } from "@/components/ui/verdict-badge";
import { WhatsAppPhone } from "@/components/whatsapp-phone";

const signals = [
  {
    icon: FileSearch,
    name: "Forensic detection",
    text: "An ensemble hunts synthesis artifacts per modality — image, audio, video — tuned Indic-first, not ported from English.",
  },
  {
    icon: Fingerprint,
    name: "Provenance parsing",
    text: "C2PA credentials, EXIF, and watermark signatures read wherever present.",
  },
  {
    icon: ShieldCheck,
    name: "Authenticity contradiction",
    text: "Declared provenance cross-checked against forensics. Untouched metadata plus synthetic pixels is the loudest alarm there is.",
  },
  {
    icon: History,
    name: "Context trace",
    text: "Earliest appearance online, with hits from PIB Fact Check, Alt News, BOOM, and Factly called out first.",
  },
  {
    icon: Hourglass,
    name: "Temporal integrity",
    text: "Declared post date weighed against earliest-seen date — recycled footage passed off as breaking news gets caught.",
  },
];

export default function Home() {
  return (
    <main>
      {/* Hero: the dossier is the product. */}
      <section className="mx-auto max-w-5xl px-4 pb-16 pt-14 sm:pt-20">
        <div className="grid items-center gap-10 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="dossier-in">
            <h1 className="max-w-xl text-5xl font-bold leading-[1.05] tracking-tight sm:text-6xl">
              Before you forward it,{" "}
              <span className="font-display font-normal italic">know what it is.</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-ink-soft">
              Lumen checks suspicious images, voice notes, videos, and links for signs of
              AI generation — and explains the verdict in plain language, starting with
              Malayalam, Hindi, Tamil, and Telugu.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/analyze">
                <Button>Check a file or link</Button>
              </Link>
              <Link href="/whatsapp">
                <Button variant="outline">
                  <MessageCircle className="size-4" aria-hidden />
                  Forward via WhatsApp
                </Button>
              </Link>
            </div>
          </div>

          {/* Specimen dossier: live verdict card with lens sweep. */}
          <div
            aria-hidden
            className="dossier-in dossier-in-1 relative overflow-hidden rounded-3xl border border-line bg-white p-6"
          >
            <div className="relative mb-5 h-40 overflow-hidden rounded-2xl bg-ink">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,#0ea5e9_0%,transparent_55%),radial-gradient(circle_at_75%_80%,#0369a1_0%,transparent_60%)]" />
              <div className="scan-sweep absolute left-2 right-2 h-10 rounded-full bg-signal/40 blur-md" />
            </div>
            <VerdictBadge verdict="contradiction_detected" />
            <p className="mt-3 font-display text-2xl italic leading-snug">
              Claims to be untouched. The pixels disagree.
            </p>
            <p className="mt-3 font-mono text-xs text-ink-soft">case 9f2c…41ad · audio · whatsapp</p>
          </div>
        </div>
      </section>

      {/* Five signals: a real sequence, so numbered steps earn their numbers. */}
      <section aria-label="How Lumen reasons" className="border-y border-line bg-white">
        <div className="mx-auto max-w-5xl px-4 py-16">
          <h2 className="max-w-lg text-3xl font-bold tracking-tight">
            One classifier is an opinion. Five signals are evidence.
          </h2>
          <ol className="mt-10 list-none p-0">
            {signals.map((s, i) => (
              <li
                key={s.name}
                className="grid gap-3 border-t border-line py-6 sm:grid-cols-[3rem_14rem_1fr] sm:gap-6"
              >
                <span className="font-mono text-sm text-ink-soft">0{i + 1}</span>
                <span className="flex items-center gap-2 font-semibold">
                  <s.icon className="size-5 text-primary" aria-hidden />
                  {s.name}
                </span>
                <span className="max-w-2xl leading-relaxed text-ink-soft">{s.text}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* WhatsApp band: the front door, not a footnote. */}
      <section className="mx-auto max-w-5xl px-4 py-16">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div>
            <h2 className="max-w-md text-3xl font-bold tracking-tight">
              Fraud travels by forward. So does the truth now.
            </h2>
            <p className="mt-4 max-w-md leading-relaxed text-ink-soft">
              Send the sandbox join code once, then forward any suspicious voice note,
              video, or image. Lumen replies with a verdict and a link to the full
              report — same pipeline as the web upload, no second-class detection.
            </p>
            <div className="mt-6">
              <Link href="/whatsapp">
                <Button variant="outline">How WhatsApp checks work</Button>
              </Link>
            </div>
            <p className="mt-6 flex items-center gap-2 text-sm text-ink-soft">
              <AudioLines className="size-4 text-primary" aria-hidden />
              Built first for Malayalam, Hindi, Tamil, and Telugu voice notes.
            </p>
          </div>
          <div className="dossier-in-2 flex justify-center">
            <WhatsAppPhone
              lines={[
                "Likely synthetic — this voice note carries generation artifacts in the 2–4 kHz band.",
                "Full evidence: lumen.report/r/9f2c41ad",
              ]}
            />
          </div>
        </div>
      </section>
    </main>
  );
}
