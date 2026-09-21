import { Chrome } from "lucide-react";
import { Brand } from "@/components/brand/logo";
import { StatusPill } from "@/components/brand/status-pill";

export const metadata = {
  title: "Login",
  description: "Acesso institucional ao cockpit IQOperator.",
};

export default function LoginPage() {
  return (
    <main className="relative z-10 flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm rounded-xl border border-border bg-surface p-8">
        <div className="flex flex-col items-center text-center">
          <Brand />
          <p className="mt-4 text-sm text-muted">
            Acesso institucional ao cockpit
          </p>
          <StatusPill status="offline" label="login necessário" className="mt-4" />
        </div>

        <a
          href="/api/auth/signin"
          className="mt-8 flex w-full items-center justify-center gap-2 rounded-lg bg-foreground px-4 py-3 text-sm font-semibold text-black transition-opacity hover:opacity-90"
        >
          <Chrome size={18} aria-hidden />
          Continuar com Google
        </a>

        <p className="mt-4 text-center text-xs text-muted">
          Acesso restrito a e-mails autorizados.
        </p>

        <a
          href="/dashboard"
          className="mt-6 block text-center text-sm text-muted underline-offset-4 hover:text-foreground hover:underline"
        >
          voltar ao dashboard
        </a>
      </div>
    </main>
  );
}
