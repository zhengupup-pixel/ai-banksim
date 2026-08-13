type MetricProps = {
  label: string;
  value: string;
};

export function Metric({ label, value }: MetricProps) {
  return (
    <div className="border border-slate-200 bg-white p-4">
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-ink">{value}</div>
    </div>
  );
}

