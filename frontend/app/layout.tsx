import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Outfit, Source_Serif_4 } from "next/font/google";
import { BRAND } from "@/lib/brand";
import { Providers } from "@/app/providers";
import "./globals.css";

const outfit = Outfit({ subsets: ["latin", "latin-ext"], variable: "--font-outfit", display: "swap" });
const inter = Inter({ subsets: ["latin", "latin-ext", "vietnamese"], variable: "--font-inter", display: "swap" });
const sourceSerif = Source_Serif_4({ subsets: ["latin", "latin-ext", "vietnamese"], variable: "--font-source-serif", display: "swap" });
const jetbrains = JetBrains_Mono({ subsets: ["latin", "latin-ext", "vietnamese"], variable: "--font-jetbrains-mono", display: "swap" });

export const metadata: Metadata = {
  title: { default: `${BRAND.name} — ${BRAND.tagline}`, template: `%s · ${BRAND.name}` },
  description: BRAND.description,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" suppressHydrationWarning className={`${outfit.variable} ${inter.variable} ${sourceSerif.variable} ${jetbrains.variable}`}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
