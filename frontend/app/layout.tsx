import "./globals.css";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { LanguageProvider } from "@/context/LanguageContext";
import GlobalNotificationListener from "@/components/GlobalNotificationListener";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "NexusAI - AI Workforce",
  description: "AI Workforce platform for Pakistani SMEs",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-[#0a0f18] text-white antialiased`}>
        <LanguageProvider>
          {children}
          <GlobalNotificationListener />
        </LanguageProvider>
      </body>
    </html>
  );
}
