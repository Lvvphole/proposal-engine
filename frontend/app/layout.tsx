import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Proposal Engine",
  description: "AI-powered contractor proposal generation from supplier quotes.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
