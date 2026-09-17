import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Jack AI",
  description: "A premium AI chat wrapper.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}