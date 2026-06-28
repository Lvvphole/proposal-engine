import type { Metadata } from "next";
import "./globals.css";
import AuthGate from "../components/AuthGate";

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
      <body>
        <AuthGate>{children}</AuthGate>
      </body>
    </html>
  );
}
