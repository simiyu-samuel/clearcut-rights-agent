import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ClearCut — Rights clearance workspace",
  description: "Evidence-backed rights clearance for film and television teams.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
