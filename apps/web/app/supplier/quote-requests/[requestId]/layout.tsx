export function generateStaticParams() {
  return [
    { requestId: "demo" },
    { requestId: "sample" },
  ];
}

export default function QuoteRequestDetailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
