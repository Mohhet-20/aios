import type { Metadata } from "next";
import "@/styles/globals.css";
import { Providers } from "./providers";

// Deliberately not using next/font/google here: build environments without
// outbound access to Google Fonts (common in locked-down enterprise CI
// runners) would otherwise fail the production build. styles/globals.css
// defines --font-sans/--font-mono with a system-font fallback stack instead;
// swap in next/font/local with self-hosted Inter/JetBrains Mono files when
// deploying somewhere the exact brand typeface matters.
export const metadata: Metadata = {
  title: "AIOS — Enterprise AI Operating System",
  description: "Manage agents, prompts, workflows, memory, tools, and evaluation from one platform.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
