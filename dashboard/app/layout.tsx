import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/nav";
import { getOptionalSession } from "@/lib/auth";

export const metadata: Metadata = {
  title: "Anneal",
  description: "Dependabot for AI agent prompts and skills",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getOptionalSession();

  return (
    <html lang="en">
      <body>
        <Nav session={session} />
        <main className="min-h-screen px-4 pb-8 pt-20 md:ml-52 md:px-8 md:py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
