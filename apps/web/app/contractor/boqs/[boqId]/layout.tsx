export function generateStaticParams() {
  return [
    { boqId: "demo" },
    { boqId: "sample" },
  ];
}

export default function BoQDetailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
