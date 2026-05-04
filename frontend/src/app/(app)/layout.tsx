import PrivateHeader from "@/components/layout/private-header";
import Footer from "@/components/layout/footer";
export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <PrivateHeader />
      <main className="flex flex-1 flex-col">{children}</main>
      <Footer />
    </>
  );
}
