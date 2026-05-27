import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/nav";

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
      <body>
        <Nav />
        <main className="min-h-screen px-4 pb-8 pt-20 md:ml-52 md:px-8 md:py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
