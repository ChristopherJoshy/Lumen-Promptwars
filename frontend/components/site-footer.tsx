export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-line">
      <div className="mx-auto max-w-5xl px-4 py-10 text-sm text-ink-soft">
        <p className="max-w-2xl leading-relaxed">
          Lumen is a probabilistic analysis aid, not legal or forensic proof. Extracted
          third-party media is processed transiently and never redistributed.
        </p>
        <p className="mt-3 font-mono text-xs">case retention: analysis + short cache TTL only</p>
      </div>
    </footer>
  );
}
