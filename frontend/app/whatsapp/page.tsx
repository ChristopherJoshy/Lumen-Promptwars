import type { Metadata } from "next";
import { MessageCircle } from "lucide-react";
import { WhatsAppPhone } from "@/components/whatsapp-phone";

export const metadata: Metadata = {
  title: "WhatsApp checks",
  description:
    "Forward suspicious voice notes, videos, and images to Lumen on WhatsApp and get a verdict plus a full report link back.",
};

const steps = [
  {
    name: "Join the sandbox",
    text: "Message the join code to the Lumen sandbox number in WhatsApp. One-time setup — required because development runs on Twilio's sandbox, not a public number.",
  },
  {
    name: "Forward the suspect",
    text: "Forward any voice note, video, or image just as you received it. Anything over 16 MB gets a reply asking you to use the web upload instead.",
  },
  {
    name: "Get the verdict back",
    text: "Lumen replies with a traffic-light verdict, one plain-language sentence, and a link to the full evidence report. Same pipeline as the web upload.",
  },
];

export default function WhatsAppPage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-12">
      <p className="flex items-center gap-2 text-sm font-semibold text-primary">
        <MessageCircle className="size-4" aria-hidden />
        First-class intake, not a demo extra
      </p>
      <h1 className="mt-3 max-w-2xl text-4xl font-bold tracking-tight sm:text-5xl">
        Forward it. <span className="font-display font-normal italic">Know it.</span>
      </h1>
      <p className="mt-4 max-w-2xl text-lg leading-relaxed text-ink-soft">
        Most deepfake fraud in India circulates as WhatsApp forwards, not timeline links.
        Lumen meets it where it lives.
      </p>

      <div className="mt-12 grid gap-10 lg:grid-cols-2">
        <ol className="list-none space-y-2 p-0">
          {steps.map((s, i) => (
            <li key={s.name} className="grid gap-2 rounded-3xl border border-line bg-white p-6 sm:grid-cols-[2.5rem_1fr]">
              <span className="grid size-10 place-items-center rounded-full bg-primary font-mono text-sm font-bold text-white">
                {i + 1}
              </span>
              <div>
                <p className="font-bold">{s.name}</p>
                <p className="mt-1 text-sm leading-relaxed text-ink-soft">{s.text}</p>
              </div>
            </li>
          ))}
        </ol>
        <div className="flex items-start justify-center">
          <WhatsAppPhone
            lines={[
              "Contradiction detected — this video claims a 2026 event, but it first appeared online in 2021.",
              "Already debunked by BOOM. Full evidence: lumen.report/r/7a11c902",
            ]}
          />
        </div>
      </div>
    </main>
  );
}
