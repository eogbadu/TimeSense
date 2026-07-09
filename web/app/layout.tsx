import type { Metadata } from "next";
import { Geist, Geist_Mono, Playfair_Display } from "next/font/google";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const playfair = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: "TimeSense — Know the best next step",
  description:
    "TimeSense is a context-aware personal time assistant. It reads your calendar, tasks, energy, and location to tell you the single best thing to do now — so planning your day never becomes another job.",
  openGraph: {
    title: "TimeSense — Know the best next step",
    description:
      "A context-aware AI time assistant that tells you the one best thing to do now — from your schedule, tasks, health, and location.",
    images: ["/app-icon.png"],
  },
  icons: { icon: "/app-icon.png" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${playfair.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
