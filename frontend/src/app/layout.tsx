import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { IntegrationStatus } from "@/components/IntegrationStatus";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Omni Copilot",
  description: "Unified AI Chat Interface",
};

import { Providers } from "@/components/Providers";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-slate-950 text-slate-200 h-screen w-full flex overflow-hidden selection:bg-indigo-500/30`}>
        <Providers>
          <Sidebar />
          
          <div className="flex-1 flex flex-col min-w-0">
            <Topbar />
            <main className="flex-1 flex overflow-hidden">
              <div className="flex-1 relative overflow-y-auto">
                {children}
              </div>
              <IntegrationStatus />
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
