export type TelemetryRecord = Record<string, unknown>;

function asRecord(value: unknown): TelemetryRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as TelemetryRecord : {};
}

function positiveNumber(...values: unknown[]): number | null {
  for (const value of values) {
    const numeric = Number(value);
    if (Number.isFinite(numeric) && numeric > 0) return numeric;
  }
  return null;
}

export function estimateTextTokens(value: string): number {
  return countWords(value);
}

export function countWords(value: string): number {
  return value.trim() ? value.trim().split(/\s+/).length : 0;
}

export function isEstimatedCount(timing: TelemetryRecord, metadata: TelemetryRecord): boolean {
  const pipeline = asRecord(metadata.live_pipeline ?? metadata.pipeline);
  return !(
    Number.isFinite(Number(timing.answer_tokens)) && Number(timing.answer_tokens) > 0
    || Number.isFinite(Number(pipeline.answer_tokens)) && Number(pipeline.answer_tokens) > 0
    || Number.isFinite(Number(metadata.answer_tokens)) && Number(metadata.answer_tokens) > 0
  );
}

export function tokenRatePerSecond(
  timing: TelemetryRecord,
  metadata: TelemetryRecord,
  content: string,
  elapsedMs = 0,
): number | null {
  const pipeline = asRecord(metadata.live_pipeline ?? metadata.pipeline);
  const tokens = positiveNumber(
    timing.answer_tokens,
    pipeline.answer_tokens,
    metadata.answer_tokens,
  ) ?? estimateTextTokens(content);
  const measuredMs = positiveNumber(
    timing.rate_duration_ms,
    timing.total_gen_ms,
    pipeline.rate_duration_ms,
    pipeline.total_gen_ms,
    metadata.processing_time_ms,
    pipeline.elapsed_ms,
    elapsedMs,
  );

  if (tokens > 0 && measuredMs) return tokens / (measuredMs / 1000);

  const explicit = positiveNumber(
    timing.tokens_per_second,
    timing.tokens_per_sec,
    metadata.tokens_per_second,
    pipeline.tokens_per_second,
  );
  return explicit;
}

export function formatTokenRate(
  timing: TelemetryRecord,
  metadata: TelemetryRecord,
  content: string,
  elapsedMs = 0,
): string {
  const rate = tokenRatePerSecond(timing, metadata, content, elapsedMs);
  return rate ? `${rate.toFixed(1)} tok/s` : "— tok/s";
}

export function formatWordRate(words: number, elapsedMs: number): string {
  if (!words || !elapsedMs || elapsedMs <= 0) return "— W/s";
  return `${(words / (elapsedMs / 1000)).toFixed(1)} W/s`;
}
