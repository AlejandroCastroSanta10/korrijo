import SmartHeader from "@/components/layout/smart-header";
import SmartFooter from "@/components/layout/smart-footer";

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <SmartHeader />
      <main className="flex flex-1 flex-col">{children}</main>
      <SmartFooter />
    </>
  );
}