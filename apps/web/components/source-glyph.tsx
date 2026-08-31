import type { ReactNode } from "react";

type SourceKind = "document" | "video" | "audio";

const common = { fill: "none", stroke: "currentColor", strokeLinecap: "round" as const, strokeLinejoin: "round" as const, strokeWidth: 1.8 };

export function SourceGlyph({ kind }: { kind: SourceKind }) {
  const paths: Record<SourceKind, ReactNode> = {
    document: <><path {...common} d="M6 3.8h7l4.5 4.5v11.9H6z" /><path {...common} d="M13 3.8v4.7h4.5M8.8 12h5.8M8.8 15.5h5.8" /></>,
    video: <><rect {...common} height="13.5" rx="2" width="15" x="3.5" y="5.2" /><path {...common} d="m18.5 9 3-2v10l-3-2M8.8 9.1l4.5 2.9-4.5 2.9z" /></>,
    audio: <><path {...common} d="M8.2 17.2V6.8l9-2v10.4" /><path {...common} d="M8.2 16.8c0 1.7-1.5 3-3.3 3s-3.2-.8-3.2-2.1 1.4-2.4 3.2-2.7c1.1-.2 2.2 0 3.3.4M17.2 15.2c0 1.7-1.5 3-3.3 3s-3.2-.8-3.2-2.1 1.4-2.4 3.2-2.7c1.1-.2 2.2 0 3.3.4" /></>,
  };
  return <svg aria-hidden="true" className="source-glyph" viewBox="0 0 24 24">{paths[kind]}</svg>;
}
