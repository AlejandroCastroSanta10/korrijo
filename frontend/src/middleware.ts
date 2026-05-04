import { NextRequest, NextResponse } from "next/server";

const SESSION_COOKIE = "korrijo_session";

export function middleware(request: NextRequest) {
  const hasSession = request.cookies.has(SESSION_COOKIE);
  if (!hasSession) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: "/app/:path*",
};
