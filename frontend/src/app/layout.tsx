import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import Header from "@/components/layout/header";

export const metadata: Metadata = {
  title: "Korrijo",
  description: "Sistema de corrección automática de exámenes manuscritos",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>
        <Header></Header>
        {children}
        <Toaster />
      </body>
    </html>
  );
}