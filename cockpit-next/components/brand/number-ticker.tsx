"use client";

import { useEffect, useState } from "react";
import { motion, useSpring, useTransform } from "framer-motion";
import { cn } from "@/lib/utils";

type NumberTickerProps = {
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
};

export function NumberTicker({
  value,
  decimals = 2,
  prefix = "",
  suffix = "",
  className,
}: NumberTickerProps) {
  const [reduced, setReduced] = useState(false);
  const spring = useSpring(0, { duration: 0.8, bounce: 0 });
  const rounded = useTransform(spring, (v) => {
    const formatted = v.toLocaleString("pt-BR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
    return `${prefix}${formatted}${suffix}`;
  });

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (!reduced) spring.set(value);
  }, [value, spring, reduced]);

  if (reduced) {
    const staticText = `${prefix}${value.toLocaleString("pt-BR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    })}${suffix}`;
    return <span className={cn("tabular-nums", className)}>{staticText}</span>;
  }

  return <motion.span className={cn("tabular-nums", className)}>{rounded}</motion.span>;
}
