import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Compliance App",
  description: "Operational UI for deterministic compliance runs"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
