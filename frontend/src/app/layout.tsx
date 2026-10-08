import { AuthProvider } from "@/context/AuthContext";
import "./globals.css";
import type { Metadata, Viewport } from 'next';
import { Providers } from "@/components/providers";

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: "Clases Vesotel",
  description: "Gestión de Jornadas de Esquí",
  icons: {
    icon: "/logo.webp",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>
        <Providers>
          <AuthProvider>
            {children}
          </AuthProvider>
        </Providers>
      </body>
    </html>
  );
}
