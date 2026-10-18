import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JobFalcon — Agentic Career Opportunity Platform",
  description: "Evidence-backed career opportunity discovery, deterministic eligibility evaluation, and multi-dimensional recommendation system.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-zinc-50 font-sans text-zinc-900">{children}</body>
    </html>
  );
}
