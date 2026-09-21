import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AppBackground } from "@/components/brand/app-background";

export const metadata: Metadata = {
  title: { default: "IQOperator — microfactx", template: "%s · IQOperator" },
  description: "Cockpit institucional do bot de trading IQOperator — winrate, equity, risco e execução em tempo real.",
  icons: { icon: "/icon.svg", apple: "/icon.svg" },
};

export const viewport: Viewport = {
  themeColor: "#0B0E14",
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