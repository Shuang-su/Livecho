export interface TextMutation {
  /** Accepted sequence; display order and coalescing key for its segment row. */
  seq: bigint;
  eventId: string;
  segmentId: string;
  text: string;
  isFinal: boolean;
  /** Local monotonic receipt time in milliseconds. */
  receivedAt: number;
  /** UTF-8 bytes of the validated serialized JSON, counted before enqueue. */
  byteSize: number;
}

export interface DisplayRow {
  seq: bigint;
  eventId: string;
  segmentId: string;
  text: string;
  byteSize: number;
}

export const DELAY_MIN_MS = 0;
export const DELAY_MAX_MS = 5_000;
export const DELAY_STEP_MS = 100;
export const MAX_PENDING_MUTATIONS = 128;
export const MAX_PENDING_BYTES = 262_144;
export const MAX_DISPLAY_TEXT_BYTES = 131_072;
export const FINAL_ROW_LIMIT = 4;

export type EnqueueResult = { ok: true } | { ok: false; overflow: true };

export interface EngineNotices {
  /**
   * Sticky local overflow gap: either presentation queue limit was hit or a
   * whole accepted row could not fit the display budget. Remains visible
   * until the viewer dismisses it or leaves the view.
   */
  overflow: boolean;
}

export interface ClearResult {
  /** True when accepted-but-undisplayed text was discarded. */
  droppedUndisplayed: boolean;
}

export function isValidDelay(ms: number): boolean {
  return (
    Number.isInteger(ms) &&
    ms >= DELAY_MIN_MS &&
    ms <= DELAY_MAX_MS &&
    ms % DELAY_STEP_MS === 0
  );
}

function textBytes(text: string): number {
  return new TextEncoder().encode(text).length;
}

export interface SchedulerClock {
  now(): number;
}

/**
 * Bounded, purely in-memory presentation scheduler for accepted text
 * mutations.
 *
 * The receive cursor and protocol metadata live in the domain; this engine
 * owns only display. Every mutation keeps its source `seq` and text
 * unmodified; the session-only delay only changes when an accepted mutation
 * becomes visible (`receivedAt + delay`), never what it contains. Status and
 * control handling never passes through this queue.
 */
export class PresentationEngine {
  private delayMsValue = DELAY_MIN_MS;
  private readonly pending: TextMutation[] = [];
  private pendingBytes = 0;
  private partialRow: DisplayRow | null = null;
  private finalRowsValue: DisplayRow[] = [];
  private displayedBytes = 0;
  private blockedValue = false;
  private overflowNotice = false;
  private admissionHalted = false;
  private appliedMutationsValue = 0;
  private renderLagMaxMsValue = 0;
  private pendingPeakValue = 0;
  private pendingBytesPeakValue = 0;

  constructor(private readonly clock: SchedulerClock) {}

  get delayMs(): number {
    return this.delayMsValue;
  }

  get partial(): DisplayRow | null {
    return this.partialRow;
  }

  get finalRows(): readonly DisplayRow[] {
    return this.finalRowsValue;
  }

  get blocked(): boolean {
    return this.blockedValue;
  }

  get notices(): EngineNotices {
    return { overflow: this.overflowNotice };
  }

  get pendingPeak(): number {
    return this.pendingPeakValue;
  }

  get pendingBytesPeak(): number {
    return this.pendingBytesPeakValue;
  }

  /** Earliest pending due time (`receivedAt + delay`), or null when empty. */
  earliestPendingDue(): number | null {
    const first = this.pending[0];
    return first === undefined ? null : first.receivedAt + this.delayMsValue;
  }

  get appliedMutations(): number {
    return this.appliedMutationsValue;
  }

  get renderLagMaxMs(): number {
    return this.renderLagMaxMsValue;
  }

  /**
   * After a queue overflow the engine stops admitting display mutations until
   * a new handshake resumes presentation.
   */
  haltAdmission(): void {
    this.admissionHalted = true;
  }

  resumeAdmission(): void {
    this.admissionHalted = false;
  }

  /** Session-only display delay in [0, 5000] ms with 100 ms steps. */
  setDelay(ms: number): boolean {
    if (!isValidDelay(ms)) return false;
    if (ms === this.delayMsValue) return true;
    this.delayMsValue = ms;
    this.drain();
    return true;
  }

  /**
   * Admit one accepted text mutation. Intermediate partial revisions may be
   * coalesced for presentation only, after protocol validation. Either queue
   * limit stops admission, clears pending and displayed text, and reports
   * overflow so the caller can close the viewer connection with a visible gap.
   */
  enqueueText(mutation: TextMutation): EnqueueResult {
    if (this.blockedValue || this.admissionHalted) return { ok: true };

    const existingIndex = this.pending.findIndex((item) => item.segmentId === mutation.segmentId);
    if (existingIndex >= 0) {
      const existing = this.pending[existingIndex]!;
      if (existing.isFinal) {
        // A finalized segment never shows a later partial, and one final per
        // segment is immutable at the protocol layer.
        return { ok: true };
      }
      if (
        this.pendingBytes - existing.byteSize + mutation.byteSize >
        MAX_PENDING_BYTES
      ) {
        return this.overflow();
      }
      this.pending[existingIndex] = mutation;
      this.pendingBytes = this.pendingBytes - existing.byteSize + mutation.byteSize;
      this.recordPeaks();
      this.drain();
      return { ok: true };
    }

    if (
      this.pending.length + 1 > MAX_PENDING_MUTATIONS ||
      this.pendingBytes + mutation.byteSize > MAX_PENDING_BYTES
    ) {
      return this.overflow();
    }

    const insertIndex = this.pending.findIndex((item) => item.seq > mutation.seq);
    if (insertIndex < 0) this.pending.push(mutation);
    else this.pending.splice(insertIndex, 0, mutation);
    this.pendingBytes += mutation.byteSize;
    this.recordPeaks();
    this.drain();
    return { ok: true };
  }

  private overflow(): EnqueueResult {
    this.pending.length = 0;
    this.pendingBytes = 0;
    this.clearRows();
    this.overflowNotice = true;
    this.admissionHalted = true;
    return { ok: false, overflow: true };
  }

  /**
   * Apply every pending mutation whose due time has passed, in accepted
   * sequence order. Records the worst observed receive-to-render lag beyond
   * the selected delay on the local monotonic clock.
   */
  drain(now: number = this.clock.now()): void {
    while (this.pending.length > 0) {
      const next = this.pending[0]!;
      if (next.receivedAt + this.delayMsValue > now) break;
      this.pending.shift();
      this.pendingBytes -= next.byteSize;
      const lag = now - (next.receivedAt + this.delayMsValue);
      if (lag > this.renderLagMaxMsValue) this.renderLagMaxMsValue = lag;
      this.appliedMutationsValue += 1;
      this.apply(next);
    }
  }

  private apply(mutation: TextMutation): void {
    if (this.blockedValue) return;
    if (this.finalRowsValue.some((row) => row.segmentId === mutation.segmentId)) return;

    const byteSize = textBytes(mutation.text);
    if (byteSize > MAX_DISPLAY_TEXT_BYTES) {
      // A whole accepted row cannot fit: clear the view, never truncate.
      this.clearRows();
      this.overflowNotice = true;
      return;
    }

    if (!mutation.isFinal) {
      if (this.partialRow !== null) this.displayedBytes -= this.partialRow.byteSize;
      this.partialRow = { ...mutation, byteSize };
      this.displayedBytes += byteSize;
      this.evictForDisplayBytes();
      return;
    }

    if (this.partialRow !== null && this.partialRow.segmentId === mutation.segmentId) {
      this.displayedBytes -= this.partialRow.byteSize;
      this.partialRow = null;
    }
    this.finalRowsValue.push({ ...mutation, byteSize });
    this.displayedBytes += byteSize;
    while (this.finalRowsValue.length > FINAL_ROW_LIMIT) {
      const oldest = this.finalRowsValue.shift();
      if (oldest !== undefined) this.displayedBytes -= oldest.byteSize;
    }
    this.evictForDisplayBytes();
  }

  private evictForDisplayBytes(): void {
    while (this.displayedBytes > MAX_DISPLAY_TEXT_BYTES && this.finalRowsValue.length > 0) {
      const oldest = this.finalRowsValue.shift();
      if (oldest !== undefined) this.displayedBytes -= oldest.byteSize;
    }
  }

  /** Clear pending and displayed text (disconnect, resync, or block). */
  clearTextAndQueue(): ClearResult {
    const droppedUndisplayed = this.pending.length > 0;
    this.pending.length = 0;
    this.pendingBytes = 0;
    this.clearRows();
    return { droppedUndisplayed };
  }

  /** Terminal statuses block further transcript presentation immediately. */
  blockAndClearText(): ClearResult {
    this.blockedValue = true;
    return this.clearTextAndQueue();
  }

  /** New binding/resync: unblock, resume admission, drop display state. */
  reset(): void {
    this.blockedValue = false;
    this.admissionHalted = false;
    this.clearTextAndQueue();
  }

  /** Viewer dismissed the local overflow gap notice. */
  dismissOverflow(): void {
    this.overflowNotice = false;
  }

  private clearRows(): void {
    this.partialRow = null;
    this.finalRowsValue = [];
    this.displayedBytes = 0;
  }

  private recordPeaks(): void {
    if (this.pending.length > this.pendingPeakValue) this.pendingPeakValue = this.pending.length;
    if (this.pendingBytes > this.pendingBytesPeakValue) this.pendingBytesPeakValue = this.pendingBytes;
  }
}
