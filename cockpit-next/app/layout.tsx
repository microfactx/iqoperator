import type { Metadata } from "next";
import "./globals.css";
import { AppBackground } from "@/components/brand/app-background";

export const metadata: Metadata = {
  title: { default: "IQOperator — microfactx", template: "%s · IQOperator" },
  description: "Cockpit institucional do bot de trading IQOperator — winrate, equity, risco e execução em tempo real.",
  themeColor: "#0B0E14",
  icons: { icon: "/icon.svg", apple: "/icon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className="dark">
      <body className="min-h-screen antialiased">
        <AppBackground />
        {children}
      </body>
    </html>
  );
}