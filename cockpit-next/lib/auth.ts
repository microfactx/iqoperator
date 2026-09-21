import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
export const { handlers, auth, signIn, signOut } = NextAuth({
  trustHost: true,
  secret: process.env.AUTH_SECRET || "dev-secret-change-me",
  providers: [Google],
  callbacks: {
    async signIn({ profile }){
      const allow = (process.env.ALLOWED_EMAILS||"").split(",").map(s=>s.trim()).filter(Boolean);
      const domain = process.env.ALLOWED_DOMAIN;
      const email = (profile as {email?:string})?.email || "";
      if(allow.length) return allow.includes(email);
      if(domain) return email.endsWith(`@${domain}`);
      return true;
    }
  }
});
