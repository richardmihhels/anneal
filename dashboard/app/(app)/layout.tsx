import { Nav } from "@/components/nav";
import { getOptionalSession } from "@/lib/auth";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getOptionalSession();

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-zinc-100">
      <Nav session={session} />
      <main className="min-h-screen px-4 pb-8 pt-20 md:ml-52 md:px-8 md:py-8">
        {children}
      </main>
    </div>
  );
}
