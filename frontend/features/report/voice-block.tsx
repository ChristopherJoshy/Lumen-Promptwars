import type { CaseSignals } from "./api";

/** Voice-note block: detected language + transcript + English translation. */
export function VoiceBlock({ sarvam }: { sarvam?: CaseSignals["sarvam"] }) {
  const result = sarvam?.result;
  if (!result?.transcript && !sarvam?.warning) return null;
  const lang = (result?.detected_language || "unknown").toLowerCase();
  return (
    <section aria-label="Voice note transcript" className="mt-8 rounded-3xl border border-gridline bg-console p-6">
      <h2 className="font-lab text-xl font-semibold tracking-tight text-foam">Voice note</h2>
      <p className="mt-2 font-mono text-xs tracking-widest text-scan uppercase">
        Detected language: {lang}
      </p>
      {result?.transcript ? (
        <>
          <blockquote lang={lang} className="mt-3 border-l-2 border-scan pl-4 leading-relaxed text-foam">
            {result.transcript.length > 600 ? (
              <details>
                <summary className="cursor-pointer">
                  {result.transcript.slice(0, 600)}… <span className="text-scan">(more)</span>
                </summary>
                <span>{result.transcript}</span>
              </details>
            ) : (
              result.transcript
            )}
          </blockquote>
          {result.translated_en && (
            <p lang="en" className="mt-3 text-sm leading-relaxed text-fog">
              <span className="font-semibold text-foam">English: </span>
              {result.translated_en}
            </p>
          )}
          <p className="mt-3 text-xs text-fog">
            Code-mixing (Hinglish, Tanglish) is normal speech, not a synthetic tell.
          </p>
        </>
      ) : (
        <p className="mt-2 text-sm text-fog">{sarvam?.warning ?? "No transcript available."}</p>
      )}
    </section>
  );
}
