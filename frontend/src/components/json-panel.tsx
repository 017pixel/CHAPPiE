type JsonPanelProps = {
  value: unknown;
};

export function JsonPanel({ value }: JsonPanelProps) {
  return <pre className="overflow-auto rounded-3xl bg-ink p-5 text-xs leading-6 text-white">{JSON.stringify(value, null, 2)}</pre>;
}
