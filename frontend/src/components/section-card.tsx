import { PropsWithChildren } from "react";

type SectionCardProps = PropsWithChildren<{
  eyebrow: string;
  title: string;
  subtitle?: string;
  className?: string;
}>;

export function SectionCard({ eyebrow, title, subtitle, children, className }: SectionCardProps) {
  return (
    <section className={`rounded-none border border-white/5 bg-night p-8 shadow-glass transition-all hover:border-white/10 ${className}`}>
      <p className="text-[10px] uppercase font-bold tracking-[0.4em] text-ember">{eyebrow}</p>
      <h2 className="mt-5 text-3xl font-bold tracking-tight text-mist">{title}</h2>
      {subtitle ? <p className="mt-3 text-sm leading-relaxed text-slate max-w-2xl">{subtitle}</p> : null}
      <div className="mt-10">{children}</div>
    </section>
  );
}
