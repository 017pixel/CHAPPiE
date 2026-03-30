import { useQuery } from "@tanstack/react-query";

type DataPageProps = {
  title: string;
  subtitle: string;
  queryKey: string;
  queryFn: () => Promise<unknown>;
};

export function DataPage({ title, subtitle, queryKey, queryFn }: DataPageProps) {
  const query = useQuery({ queryKey: [queryKey], queryFn });

  return (
    <section className="rounded-[2rem] bg-white p-5 shadow-panel">
      <p className="text-xs uppercase tracking-[0.3em] text-slate">{queryKey}</p>
      <h2 className="mt-2 text-3xl font-bold">{title}</h2>
      <p className="mt-2 text-sm text-slate">{subtitle}</p>
      <pre className="mt-5 overflow-auto rounded-3xl bg-ink p-5 text-xs leading-6 text-white">
        {query.isLoading ? "Lade Daten..." : JSON.stringify(query.data, null, 2)}
      </pre>
    </section>
  );
}
