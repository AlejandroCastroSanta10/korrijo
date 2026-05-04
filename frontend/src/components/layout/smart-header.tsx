"use client";

import Header from "./header";
import PrivateHeader from "./private-header";
import { useCurrentUser } from "@/lib/hooks/auth";

export default function SmartHeader() {
  const { data: user } = useCurrentUser();
  return user ? <PrivateHeader /> : <Header />;
}
