import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { AuthGate } from "@/components/auth-gate";

export const metadata: Metadata = {
  title: "ClearCut — Rights clearance workspace",
  description: "Evidence-backed rights clearance for film and television teams.",
  icons: {
    icon: "/icon.png",
    shortcut: "/icon.png",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body><AuthProvider><AuthGate>{children}</AuthGate></AuthProvider></body>
    </html>
  );
}
