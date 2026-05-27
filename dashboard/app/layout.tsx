import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Anneal",
  description: "Dependabot for AI agent prompts and skills",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
