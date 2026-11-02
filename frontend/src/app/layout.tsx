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
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <body className="min-h-full flex flex-col bg-zinc-50 dark:bg-zinc-950 font-sans text-zinc-900 dark:text-zinc-100 antialiased selection:bg-teal-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
