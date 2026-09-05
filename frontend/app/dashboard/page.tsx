import { Inbox } from "lucide-react";

export default function DashboardPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-4xl font-bold tracking-tight">
        Your <span className="font-display font-normal italic">dossiers.</span>
      </h1>
      <div className="mt-8 flex flex-col items-center gap-3 rounded-3xl border border-line bg-white px-6 py-16 text-center">
        <Inbox className="size-8 text-ink-soft" aria-hidden />
        <p className="font-semibold">Nothing here yet</p>
        <p className="max-w-sm text-sm leading-relaxed text-ink-soft">
          Submissions you check while signed in will appear here with their verdicts.
          Sign-in lands with auth in checkpoint 15.
        </p>
      </div>
    </main>
  );
}
