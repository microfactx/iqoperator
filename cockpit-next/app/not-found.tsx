import Link from "next/link";
import { LogoMark } from "@/components/brand/logo";

export default function NotFound() {
  return (
    <main className="relative z-10 flex min-h-screen flex-col items-center justify-center px-4 py-12 text-center">
      <LogoMark size={72} />
      <h1 className="mt-6 text-6xl font-extrabold tracking-tight text-foreground">
        404
      </h1>
      <p className="mt-2 text-lg font-semibold text-foreground">
        Página não encontrada
      </p>
      <Link
        href="/dashboard"
        className="mt-8 inline-flex items-center justify-center rounded-lg bg-foreground px-6 py-3 text-sm font-semibold text-black transition-opacity hover:opacity-90"
      >
        Voltar ao cockpit
      </Link>
      <p className="mt-4 text-sm text-muted">
        A rota acessada não existe ou foi movida.
      </p>
    </main>
  );
}
