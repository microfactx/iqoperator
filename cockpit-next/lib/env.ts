import { z } from "zod";
const envSchema = z.object({
  TRADE_LOG: z.string().default("data/trades_live.csv"),
  DATABASE_URL: z.string().optional(),
  HF_TOKEN: z.string().optional(),
  HF_DATASET_REPO: z.string().default("jonatanciamarro/iqoperator-trades"),
  AUTH_SECRET: z.string().optional(),
  GOOGLE_CLIENT_ID: z.string().optional(),
  GOOGLE_CLIENT_SECRET: z.string().optional(),
});
export const env = envSchema.parse(process.env);
