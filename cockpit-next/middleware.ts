import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";
export async function middleware(req: Request){
  const session = await auth();
  const url = new URL(req.url);
  if(!session && !url.pathname.startsWith("/api/auth") && url.pathname!=="/login"){
    return NextResponse.redirect(new URL("/login", req.url));
  }
  return NextResponse.next();
}
export const config = { matcher: ["/((?!api/auth|_next|favicon|login).*)"] };
