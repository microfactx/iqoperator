import { NextResponse } from "next/server";
export async function middleware(req: Request){
  // sem AUTH_SECRET/GOOGLE vars em dev, deixa passar (cockpit aberto)
  if(!process.env.GOOGLE_CLIENT_ID || !process.env.AUTH_SECRET){
    return NextResponse.next();
  }
  const { auth } = await import("@/lib/auth");
  const session = await auth();
  const url = new URL(req.url);
  if(!session && !url.pathname.startsWith("/api/auth") && url.pathname!=="/login"){
    return NextResponse.redirect(new URL("/login", req.url));
  }
  return NextResponse.next();
}
export const config = { matcher: ["/((?!api/auth|_next|favicon|login).*)"] };
