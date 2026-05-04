"use client";

import Footer from "./footer";
import { useCurrentUser } from "@/lib/hooks/auth";

export default function SmartFooter() {
  const { data: user } = useCurrentUser();
  return <Footer homeHref={user ? "/app/new" : "/login"} />;
}
