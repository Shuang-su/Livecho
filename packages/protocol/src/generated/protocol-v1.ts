export type ProtocolMessageV1 =
  | WorkerHelloV1
  | WorkerWelcomeV1
  | LeaseV1
  | LeaseCancelV1
  | HeartbeatV1
  | WorkerStatsV1
  | TranscriptSegmentV1
  | TimelineEventV1
  | ViewerSubscribeV1
  | ViewerReadyV1
  | ProtocolAckV1
  | ProtocolErrorV1;
/**
 * @minItems 1
 * @maxItems 16
 */
export type Capabilities = ("asr.transcribe" | "protocol.binary-pcm")[];
export type MessageId = string;
export type ModelId = string;
export type Provider = string;
export type Revision = string;
export type Sha256 = string;
/**
 * @maxItems 16
 */
export type ModelManifests = ModelManifestRefV1[];
export type Protocol = "livecho.worker.v1";
export type ProtocolMinor = 0;
export type ConnectionId = string;
export type Epoch = string;
export type LeaseId = string;
export type NextInputSeq = string;
export type NextOutputSeq = string;
export type SessionId = string;
export type SentAt = string;
/**
 * @minItems 1
 * @maxItems 16
 */
export type SupportedMinors = number[];
export type Type = "worker.hello";
export type WorkerId = string;
export type WorkerVersion = string;
/**
 * @minItems 2
 * @maxItems 2
 */
export type AcceptedCapabilities = ("asr.transcribe" | "protocol.binary-pcm")[];
/**
 * @maxItems 16
 */
export type AcceptedManifests = ModelManifestRefV1[];
export type ConnectionId1 = string;
export type MessageId1 = string;
export type MinimumWorkerVersion = "0.1.0";
export type Protocol1 = "livecho.worker.v1";
export type ProtocolMinor1 = 0;
export type ResumeSucceeded = boolean;
export type SelectedMinor = 0;
export type SentAt1 = string;
export type Type1 = "worker.welcome";
export type Channels = 1;
export type Encoding = "pcm_s16le";
export type SampleRateHz = 16000;
export type AudioOrigin = "synthetic";
export type Epoch1 = string;
export type ExpiresAt = string;
export type InputStartSeq = string;
export type IssuedAt = string;
export type LeaseId1 = string;
export type MessageId2 = string;
export type OutputStartSeq = string;
export type Protocol2 = "livecho.worker.v1";
export type ProtocolMinor2 = 0;
export type Revision1 = string;
export type RoomId = string;
export type SentAt2 = string;
export type SessionId1 = string;
export type Type2 = "worker.lease";
export type Epoch2 = string;
export type ExpectedRevision = string;
export type LeaseId2 = string;
export type MessageId3 = string;
export type Protocol3 = "livecho.worker.v1";
export type ProtocolMinor3 = 0;
export type Reason =
  "operator_stop" | "lease_expired" | "worker_replaced" | "policy_disable" | "protocol_violation" | "session_end";
export type SentAt3 = string;
export type SessionId2 = string;
export type Type3 = "worker.lease_cancel";
export type AudioBufferBytes = number;
export type Epoch3 = string;
export type LastInputSeq = string | null;
export type LastOutputSeq = string | null;
export type LeaseId3 = string;
export type MessageId4 = string;
export type ObservedAt = string;
export type Protocol4 = "livecho.worker.v1";
export type ProtocolMinor4 = 0;
export type SentAt4 = string;
export type Seq = string;
export type SessionId3 = string;
export type State = "ready" | "busy" | "draining" | "error";
export type Type4 = "worker.heartbeat";
export type Epoch4 = string;
export type LeaseId4 = string;
export type MessageId5 = string;
export type ProcessedAudioMs = string;
export type Protocol5 = "livecho.worker.v1";
export type ProtocolMinor5 = 0;
export type RealtimeFactor = number;
export type Revision2 = string;
export type SegmentsAccepted = string;
export type SegmentsRejected = string;
export type SentAt5 = string;
export type Seq1 = string;
export type SessionId4 = string;
export type StatsId = string;
export type Type5 = "worker.stats";
export type WindowEndedAt = string;
export type WindowStartedAt = string;
export type Confidence = number | null;
export type EndMs = number;
export type Epoch5 = string;
export type IsFinal = boolean;
export type Language = string | null;
export type LeaseId5 = string;
export type MessageId6 = string;
export type Protocol6 = "livecho.worker.v1";
export type ProtocolMinor6 = 0;
export type Revision3 = string;
export type SegmentId = string;
export type SentAt6 = string;
export type Seq2 = string;
export type SessionId5 = string;
export type StartMs = number;
export type Text = string;
export type Type6 = "worker.transcript";
export type Epoch6 = string;
export type EventId = string;
export type MessageId7 = string;
export type OccurredAt = string;
export type Payload = TranscriptTimelinePayloadV1 | SessionStatusTimelinePayloadV1;
export type Confidence1 = number | null;
export type EndMs1 = number;
export type IsFinal1 = boolean;
export type Language1 = string | null;
export type SegmentId1 = string;
export type StartMs1 = number;
export type Text1 = string;
export type ReasonCode = string | null;
export type Status = "starting" | "live" | "stopping" | "stopped" | "failed";
export type Protocol7 = "livecho.viewer.v1";
export type ProtocolMinor7 = 0;
export type Revision4 = string;
export type RoomId1 = string;
export type SentAt7 = string;
export type Seq3 = string;
export type SessionId6 = string;
export type Type7 = "viewer.timeline_event";
export type ClientVersion = string;
export type Epoch7 = string;
export type NextSeq = string;
export type SessionId7 = string;
export type MessageId8 = string;
export type Protocol8 = "livecho.viewer.v1";
export type ProtocolMinor8 = 0;
export type RoomId2 = string;
export type SentAt8 = string;
/**
 * @minItems 1
 * @maxItems 16
 */
export type SupportedMinors1 = number[];
export type Type8 = "viewer.subscribe";
export type CursorResumed = boolean;
export type Epoch8 = string;
export type MessageId9 = string;
export type MinimumClientVersion = "0.1.0";
export type NextSeq1 = string;
export type Protocol9 = "livecho.viewer.v1";
export type ProtocolMinor9 = 0;
export type SelectedMinor1 = 0;
export type SentAt9 = string;
export type SessionId8 = string;
export type Type9 = "viewer.ready";
export type AcknowledgedMessageId = string;
export type ExpectedRevision1 = string | null;
export type MessageId10 = string;
export type Outcome = "accepted" | "seq_duplicate" | "revision_duplicate" | "cancel_duplicate";
export type Protocol10 = "livecho.worker.v1" | "livecho.viewer.v1";
export type ProtocolMinor10 = 0;
export type Revision5 = string | null;
export type SentAt10 = string;
export type Seq4 = string | null;
export type Type10 = "protocol.ack";
export type Code =
  | "malformed_json"
  | "duplicate_key"
  | "unknown_field"
  | "schema_invalid"
  | "control_frame_too_large"
  | "unknown_major"
  | "unsupported_minor"
  | "worker_version_too_old"
  | "capability_required"
  | "manifest_not_allowed"
  | "lease_unknown"
  | "lease_expired"
  | "lease_closed"
  | "binding_mismatch"
  | "epoch_stale"
  | "epoch_unknown"
  | "seq_conflict"
  | "seq_gap"
  | "revision_conflict"
  | "revision_stale"
  | "revision_gap"
  | "revision_immutable"
  | "revision_capacity_exceeded"
  | "cancel_conflict"
  | "object_final"
  | "resync_required"
  | "binary_header_invalid"
  | "binary_frame_too_large"
  | "audio_pts_invalid"
  | "audio_budget_exceeded";
export type Expected = string | null;
export type Message = string;
export type MessageId11 = string;
export type Protocol11 = "livecho.worker.v1" | "livecho.viewer.v1";
export type ProtocolMinor11 = 0;
export type Received = string | null;
export type Retryable = boolean;
export type SentAt11 = string;
export type Type11 = "protocol.error";

export interface WorkerHelloV1 {
  capabilities: Capabilities;
  message_id: MessageId;
  model_manifests: ModelManifests;
  protocol: Protocol;
  protocol_minor: ProtocolMinor;
  resume?: WorkerResumeV1 | null;
  sent_at: SentAt;
  supported_minors: SupportedMinors;
  type: Type;
  worker_id: WorkerId;
  worker_version: WorkerVersion;
}
export interface ModelManifestRefV1 {
  model_id: ModelId;
  provider: Provider;
  revision: Revision;
  sha256: Sha256;
}
export interface WorkerResumeV1 {
  connection_id: ConnectionId;
  epoch: Epoch;
  lease_id: LeaseId;
  next_input_seq: NextInputSeq;
  next_output_seq: NextOutputSeq;
  session_id: SessionId;
}
export interface WorkerWelcomeV1 {
  accepted_capabilities: AcceptedCapabilities;
  accepted_manifests: AcceptedManifests;
  connection_id: ConnectionId1;
  message_id: MessageId1;
  minimum_worker_version: MinimumWorkerVersion;
  protocol: Protocol1;
  protocol_minor: ProtocolMinor1;
  resume_succeeded: ResumeSucceeded;
  selected_minor: SelectedMinor;
  sent_at: SentAt1;
  type: Type1;
}
export interface LeaseV1 {
  audio_format: AudioFormatV1;
  audio_origin: AudioOrigin;
  epoch: Epoch1;
  expires_at: ExpiresAt;
  input_start_seq: InputStartSeq;
  issued_at: IssuedAt;
  lease_id: LeaseId1;
  message_id: MessageId2;
  model_manifest: ModelManifestRefV1;
  output_start_seq: OutputStartSeq;
  protocol: Protocol2;
  protocol_minor: ProtocolMinor2;
  revision: Revision1;
  room_id: RoomId;
  sent_at: SentAt2;
  session_id: SessionId1;
  type: Type2;
}
export interface AudioFormatV1 {
  channels: Channels;
  encoding: Encoding;
  sample_rate_hz: SampleRateHz;
}
export interface LeaseCancelV1 {
  epoch: Epoch2;
  expected_revision: ExpectedRevision;
  lease_id: LeaseId2;
  message_id: MessageId3;
  protocol: Protocol3;
  protocol_minor: ProtocolMinor3;
  reason: Reason;
  sent_at: SentAt3;
  session_id: SessionId2;
  type: Type3;
}
export interface HeartbeatV1 {
  audio_buffer_bytes: AudioBufferBytes;
  epoch: Epoch3;
  last_input_seq?: LastInputSeq;
  last_output_seq?: LastOutputSeq;
  lease_id: LeaseId3;
  message_id: MessageId4;
  observed_at: ObservedAt;
  protocol: Protocol4;
  protocol_minor: ProtocolMinor4;
  sent_at: SentAt4;
  seq: Seq;
  session_id: SessionId3;
  state: State;
  type: Type4;
}
export interface WorkerStatsV1 {
  epoch: Epoch4;
  lease_id: LeaseId4;
  message_id: MessageId5;
  processed_audio_ms: ProcessedAudioMs;
  protocol: Protocol5;
  protocol_minor: ProtocolMinor5;
  realtime_factor: RealtimeFactor;
  revision: Revision2;
  segments_accepted: SegmentsAccepted;
  segments_rejected: SegmentsRejected;
  sent_at: SentAt5;
  seq: Seq1;
  session_id: SessionId4;
  stats_id: StatsId;
  type: Type5;
  window_ended_at: WindowEndedAt;
  window_started_at: WindowStartedAt;
}
export interface TranscriptSegmentV1 {
  confidence?: Confidence;
  end_ms: EndMs;
  epoch: Epoch5;
  is_final: IsFinal;
  language?: Language;
  lease_id: LeaseId5;
  message_id: MessageId6;
  protocol: Protocol6;
  protocol_minor: ProtocolMinor6;
  revision: Revision3;
  segment_id: SegmentId;
  sent_at: SentAt6;
  seq: Seq2;
  session_id: SessionId5;
  start_ms: StartMs;
  text: Text;
  type: Type6;
}
export interface TimelineEventV1 {
  epoch: Epoch6;
  event_id: EventId;
  message_id: MessageId7;
  occurred_at: OccurredAt;
  payload: Payload;
  protocol: Protocol7;
  protocol_minor: ProtocolMinor7;
  revision: Revision4;
  room_id: RoomId1;
  sent_at: SentAt7;
  seq: Seq3;
  session_id: SessionId6;
  type: Type7;
}
export interface TranscriptTimelinePayloadV1 {
  confidence?: Confidence1;
  end_ms: EndMs1;
  is_final: IsFinal1;
  language?: Language1;
  segment_id: SegmentId1;
  start_ms: StartMs1;
  text: Text1;
}
export interface SessionStatusTimelinePayloadV1 {
  reason_code?: ReasonCode;
  status: Status;
}
export interface ViewerSubscribeV1 {
  client_version: ClientVersion;
  cursor?: ViewerCursorV1 | null;
  message_id: MessageId8;
  protocol: Protocol8;
  protocol_minor: ProtocolMinor8;
  room_id: RoomId2;
  sent_at: SentAt8;
  supported_minors: SupportedMinors1;
  type: Type8;
}
export interface ViewerCursorV1 {
  epoch: Epoch7;
  next_seq: NextSeq;
  session_id: SessionId7;
}
export interface ViewerReadyV1 {
  cursor_resumed: CursorResumed;
  epoch: Epoch8;
  message_id: MessageId9;
  minimum_client_version: MinimumClientVersion;
  next_seq: NextSeq1;
  protocol: Protocol9;
  protocol_minor: ProtocolMinor9;
  selected_minor: SelectedMinor1;
  sent_at: SentAt9;
  session_id: SessionId8;
  type: Type9;
}
export interface ProtocolAckV1 {
  acknowledged_message_id: AcknowledgedMessageId;
  expected_revision?: ExpectedRevision1;
  message_id: MessageId10;
  outcome: Outcome;
  protocol: Protocol10;
  protocol_minor: ProtocolMinor10;
  revision?: Revision5;
  sent_at: SentAt10;
  seq?: Seq4;
  type: Type10;
}
export interface ProtocolErrorV1 {
  code: Code;
  expected?: Expected;
  message: Message;
  message_id: MessageId11;
  protocol: Protocol11;
  protocol_minor: ProtocolMinor11;
  received?: Received;
  retryable: Retryable;
  sent_at: SentAt11;
  type: Type11;
}
