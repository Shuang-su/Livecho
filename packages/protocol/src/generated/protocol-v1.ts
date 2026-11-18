export type ProtocolMessageV1 =
  | WorkerHelloV1
  | WorkerWelcomeV1
  | WorkerWelcomeV1Minor1
  | LeaseV1
  | LeaseV1Minor1
  | LeaseCancelV1
  | LeaseCancelV1Minor1
  | HeartbeatV1
  | HeartbeatV1Minor1
  | WorkerStatsV1
  | WorkerStatsV1Minor1
  | TranscriptSegmentV1
  | TranscriptSegmentV1Minor1
  | TimelineEventV1
  | TimelineEventV1Minor1
  | ViewerSubscribeV1
  | ViewerReadyV1
  | ViewerReadyV1Minor1
  | ProtocolAckV1
  | ProtocolAckV1Minor1
  | ProtocolErrorV1
  | ProtocolErrorV1Minor1
  | EpochRotatedV1
  | ViewerResyncV1;
/**
 * @minItems 1
 * @maxItems 16
 */
export type Capabilities = ("asr.transcribe" | "protocol.binary-pcm" | "protocol.epoch-rotation")[];
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
/**
 * @minItems 3
 * @maxItems 3
 */
export type AcceptedCapabilities1 = ("asr.transcribe" | "protocol.binary-pcm" | "protocol.epoch-rotation")[];
/**
 * @maxItems 16
 */
export type AcceptedManifests1 = ModelManifestRefV1[];
export type ConnectionId2 = string;
export type MessageId2 = string;
export type MinimumWorkerVersion1 = "0.1.0";
export type Protocol2 = "livecho.worker.v1";
export type ProtocolMinor2 = 1;
export type ResumeSucceeded1 = boolean;
export type SelectedMinor1 = 1;
export type SentAt2 = string;
export type Type2 = "worker.welcome";
export type Channels = 1;
export type Encoding = "pcm_s16le";
export type SampleRateHz = 16000;
export type AudioOrigin = "synthetic";
export type Epoch1 = string;
export type ExpiresAt = string;
export type InputStartSeq = string;
export type IssuedAt = string;
export type LeaseId1 = string;
export type MessageId3 = string;
export type OutputStartSeq = string;
export type Protocol3 = "livecho.worker.v1";
export type ProtocolMinor3 = 0;
export type Revision1 = string;
export type RoomId = string;
export type SentAt3 = string;
export type SessionId1 = string;
export type Type3 = "worker.lease";
export type AudioOrigin1 = "synthetic";
export type Epoch2 = string;
export type ExpiresAt1 = string;
export type InputStartSeq1 = string;
export type IssuedAt1 = string;
export type LeaseId2 = string;
export type MessageId4 = string;
export type OutputStartSeq1 = string;
export type Protocol4 = "livecho.worker.v1";
export type ProtocolMinor4 = 1;
export type Revision2 = string;
export type RoomId1 = string;
export type SentAt4 = string;
export type SessionId2 = string;
export type Type4 = "worker.lease";
export type Epoch3 = string;
export type ExpectedRevision = string;
export type LeaseId3 = string;
export type MessageId5 = string;
export type Protocol5 = "livecho.worker.v1";
export type ProtocolMinor5 = 0;
export type Reason =
  "operator_stop" | "lease_expired" | "worker_replaced" | "policy_disable" | "protocol_violation" | "session_end";
export type SentAt5 = string;
export type SessionId3 = string;
export type Type5 = "worker.lease_cancel";
export type Epoch4 = string;
export type ExpectedRevision1 = string;
export type LeaseId4 = string;
export type MessageId6 = string;
export type Protocol6 = "livecho.worker.v1";
export type ProtocolMinor6 = 1;
export type Reason1 =
  "operator_stop" | "lease_expired" | "worker_replaced" | "policy_disable" | "protocol_violation" | "session_end";
export type SentAt6 = string;
export type SessionId4 = string;
export type Type6 = "worker.lease_cancel";
export type AudioBufferBytes = number;
export type Epoch5 = string;
export type LastInputSeq = string | null;
export type LastOutputSeq = string | null;
export type LeaseId5 = string;
export type MessageId7 = string;
export type ObservedAt = string;
export type Protocol7 = "livecho.worker.v1";
export type ProtocolMinor7 = 0;
export type SentAt7 = string;
export type Seq = string;
export type SessionId5 = string;
export type State = "ready" | "busy" | "draining" | "error";
export type Type7 = "worker.heartbeat";
export type AudioBufferBytes1 = number;
export type Epoch6 = string;
export type LastInputSeq1 = string | null;
export type LastOutputSeq1 = string | null;
export type LeaseId6 = string;
export type MessageId8 = string;
export type ObservedAt1 = string;
export type Protocol8 = "livecho.worker.v1";
export type ProtocolMinor8 = 1;
export type SentAt8 = string;
export type Seq1 = string;
export type SessionId6 = string;
export type State1 = "ready" | "busy" | "draining" | "error";
export type Type8 = "worker.heartbeat";
export type Epoch7 = string;
export type LeaseId7 = string;
export type MessageId9 = string;
export type ProcessedAudioMs = string;
export type Protocol9 = "livecho.worker.v1";
export type ProtocolMinor9 = 0;
export type RealtimeFactor = number;
export type Revision3 = string;
export type SegmentsAccepted = string;
export type SegmentsRejected = string;
export type SentAt9 = string;
export type Seq2 = string;
export type SessionId7 = string;
export type StatsId = string;
export type Type9 = "worker.stats";
export type WindowEndedAt = string;
export type WindowStartedAt = string;
export type Epoch8 = string;
export type LeaseId8 = string;
export type MessageId10 = string;
export type ProcessedAudioMs1 = string;
export type Protocol10 = "livecho.worker.v1";
export type ProtocolMinor10 = 1;
export type RealtimeFactor1 = number;
export type Revision4 = string;
export type SegmentsAccepted1 = string;
export type SegmentsRejected1 = string;
export type SentAt10 = string;
export type Seq3 = string;
export type SessionId8 = string;
export type StatsId1 = string;
export type Type10 = "worker.stats";
export type WindowEndedAt1 = string;
export type WindowStartedAt1 = string;
export type Confidence = number | null;
export type EndMs = number;
export type Epoch9 = string;
export type IsFinal = boolean;
export type Language = string | null;
export type LeaseId9 = string;
export type MessageId11 = string;
export type Protocol11 = "livecho.worker.v1";
export type ProtocolMinor11 = 0;
export type Revision5 = string;
export type SegmentId = string;
export type SentAt11 = string;
export type Seq4 = string;
export type SessionId9 = string;
export type StartMs = number;
export type Text = string;
export type Type11 = "worker.transcript";
export type Confidence1 = number | null;
export type EndMs1 = number;
export type Epoch10 = string;
export type IsFinal1 = boolean;
export type Language1 = string | null;
export type LeaseId10 = string;
export type MessageId12 = string;
export type Protocol12 = "livecho.worker.v1";
export type ProtocolMinor12 = 1;
export type Revision6 = string;
export type SegmentId1 = string;
export type SentAt12 = string;
export type Seq5 = string;
export type SessionId10 = string;
export type StartMs1 = number;
export type Text1 = string;
export type Type12 = "worker.transcript";
export type Epoch11 = string;
export type EventId = string;
export type MessageId13 = string;
export type OccurredAt = string;
export type Payload = TranscriptTimelinePayloadV1 | SessionStatusTimelinePayloadV1;
export type Confidence2 = number | null;
export type EndMs2 = number;
export type IsFinal2 = boolean;
export type Language2 = string | null;
export type SegmentId2 = string;
export type StartMs2 = number;
export type Text2 = string;
export type ReasonCode = string | null;
export type Status = "starting" | "live" | "stopping" | "stopped" | "failed";
export type Protocol13 = "livecho.viewer.v1";
export type ProtocolMinor13 = 0;
export type Revision7 = string;
export type RoomId2 = string;
export type SentAt13 = string;
export type Seq6 = string;
export type SessionId11 = string;
export type Type13 = "viewer.timeline_event";
export type Epoch12 = string;
export type EventId1 = string;
export type MessageId14 = string;
export type OccurredAt1 = string;
export type Payload1 = TranscriptTimelinePayloadV1 | SessionStatusTimelinePayloadV1;
export type Protocol14 = "livecho.viewer.v1";
export type ProtocolMinor14 = 1;
export type Revision8 = string;
export type RoomId3 = string;
export type SentAt14 = string;
export type Seq7 = string;
export type SessionId12 = string;
export type Type14 = "viewer.timeline_event";
export type ClientVersion = string;
export type Epoch13 = string;
export type NextSeq = string;
export type SessionId13 = string;
export type MessageId15 = string;
export type Protocol15 = "livecho.viewer.v1";
export type ProtocolMinor15 = 0;
export type RoomId4 = string;
export type SentAt15 = string;
/**
 * @minItems 1
 * @maxItems 16
 */
export type SupportedMinors1 = number[];
export type Type15 = "viewer.subscribe";
export type CursorResumed = boolean;
export type Epoch14 = string;
export type MessageId16 = string;
export type MinimumClientVersion = "0.1.0";
export type NextSeq1 = string;
export type Protocol16 = "livecho.viewer.v1";
export type ProtocolMinor16 = 0;
export type SelectedMinor2 = 0;
export type SentAt16 = string;
export type SessionId14 = string;
export type Type16 = "viewer.ready";
export type CursorResumed1 = boolean;
export type Epoch15 = string;
export type MessageId17 = string;
export type MinimumClientVersion1 = "0.1.0";
export type NextSeq2 = string;
export type Protocol17 = "livecho.viewer.v1";
export type ProtocolMinor17 = 1;
export type SelectedMinor3 = 1;
export type SentAt17 = string;
export type SessionId15 = string;
export type Type17 = "viewer.ready";
export type AcknowledgedMessageId = string;
export type ExpectedRevision2 = string | null;
export type MessageId18 = string;
export type Outcome = "accepted" | "seq_duplicate" | "revision_duplicate" | "cancel_duplicate";
export type Protocol18 = "livecho.worker.v1" | "livecho.viewer.v1";
export type ProtocolMinor18 = 0;
export type Revision9 = string | null;
export type SentAt18 = string;
export type Seq8 = string | null;
export type Type18 = "protocol.ack";
export type AcknowledgedMessageId1 = string;
export type ExpectedRevision3 = string | null;
export type MessageId19 = string;
export type Outcome1 = "accepted" | "seq_duplicate" | "revision_duplicate" | "cancel_duplicate";
export type Protocol19 = "livecho.worker.v1" | "livecho.viewer.v1";
export type ProtocolMinor19 = 1;
export type Revision10 = string | null;
export type SentAt19 = string;
export type Seq9 = string | null;
export type Type19 = "protocol.ack";
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
export type MessageId20 = string;
export type Protocol20 = "livecho.worker.v1" | "livecho.viewer.v1";
export type ProtocolMinor20 = 0;
export type Received = string | null;
export type Retryable = boolean;
export type SentAt20 = string;
export type Type20 = "protocol.error";
export type Code1 =
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
  | "audio_budget_exceeded"
  | "epoch_rotated"
  | "epoch_exhausted"
  | "media_time_regressed";
export type Expected1 = string | null;
export type Message1 = string;
export type MessageId21 = string;
export type Protocol21 = "livecho.worker.v1" | "livecho.viewer.v1";
export type ProtocolMinor21 = 1;
export type Received1 = string | null;
export type Retryable1 = boolean;
export type SentAt21 = string;
export type Type21 = "protocol.error";
export type ClosedEpoch = string;
export type LeaseId11 = string;
export type MediaContinueMs = number;
export type MessageId22 = string;
export type OpenedEpoch = string;
export type PcmContinuePts = string;
export type Protocol22 = "livecho.worker.v1";
export type ProtocolMinor22 = 1;
export type Reason2 = "revision_capacity" | "lease_replaced";
export type SentAt22 = string;
export type SessionId16 = string;
export type Type22 = "worker.epoch_rotated";
export type Epoch16 = string;
export type Gap = true;
export type MediaContinueMs1 = number;
export type MessageId23 = string;
export type NextSeq3 = string;
export type Protocol23 = "livecho.viewer.v1";
export type ProtocolMinor23 = 1;
export type Reason3 = "epoch_rotated" | "cursor_expired" | "cursor_unknown";
export type RoomId5 = string;
export type SentAt23 = string;
export type SessionId17 = string;
export type Type23 = "viewer.resync";

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
export interface WorkerWelcomeV1Minor1 {
  accepted_capabilities: AcceptedCapabilities1;
  accepted_manifests: AcceptedManifests1;
  connection_id: ConnectionId2;
  message_id: MessageId2;
  minimum_worker_version: MinimumWorkerVersion1;
  protocol: Protocol2;
  protocol_minor: ProtocolMinor2;
  resume_succeeded: ResumeSucceeded1;
  selected_minor: SelectedMinor1;
  sent_at: SentAt2;
  type: Type2;
}
export interface LeaseV1 {
  audio_format: AudioFormatV1;
  audio_origin: AudioOrigin;
  epoch: Epoch1;
  expires_at: ExpiresAt;
  input_start_seq: InputStartSeq;
  issued_at: IssuedAt;
  lease_id: LeaseId1;
  message_id: MessageId3;
  model_manifest: ModelManifestRefV1;
  output_start_seq: OutputStartSeq;
  protocol: Protocol3;
  protocol_minor: ProtocolMinor3;
  revision: Revision1;
  room_id: RoomId;
  sent_at: SentAt3;
  session_id: SessionId1;
  type: Type3;
}
export interface AudioFormatV1 {
  channels: Channels;
  encoding: Encoding;
  sample_rate_hz: SampleRateHz;
}
export interface LeaseV1Minor1 {
  audio_format: AudioFormatV1;
  audio_origin: AudioOrigin1;
  epoch: Epoch2;
  expires_at: ExpiresAt1;
  input_start_seq: InputStartSeq1;
  issued_at: IssuedAt1;
  lease_id: LeaseId2;
  message_id: MessageId4;
  model_manifest: ModelManifestRefV1;
  output_start_seq: OutputStartSeq1;
  protocol: Protocol4;
  protocol_minor: ProtocolMinor4;
  revision: Revision2;
  room_id: RoomId1;
  sent_at: SentAt4;
  session_id: SessionId2;
  type: Type4;
}
export interface LeaseCancelV1 {
  epoch: Epoch3;
  expected_revision: ExpectedRevision;
  lease_id: LeaseId3;
  message_id: MessageId5;
  protocol: Protocol5;
  protocol_minor: ProtocolMinor5;
  reason: Reason;
  sent_at: SentAt5;
  session_id: SessionId3;
  type: Type5;
}
export interface LeaseCancelV1Minor1 {
  epoch: Epoch4;
  expected_revision: ExpectedRevision1;
  lease_id: LeaseId4;
  message_id: MessageId6;
  protocol: Protocol6;
  protocol_minor: ProtocolMinor6;
  reason: Reason1;
  sent_at: SentAt6;
  session_id: SessionId4;
  type: Type6;
}
export interface HeartbeatV1 {
  audio_buffer_bytes: AudioBufferBytes;
  epoch: Epoch5;
  last_input_seq?: LastInputSeq;
  last_output_seq?: LastOutputSeq;
  lease_id: LeaseId5;
  message_id: MessageId7;
  observed_at: ObservedAt;
  protocol: Protocol7;
  protocol_minor: ProtocolMinor7;
  sent_at: SentAt7;
  seq: Seq;
  session_id: SessionId5;
  state: State;
  type: Type7;
}
export interface HeartbeatV1Minor1 {
  audio_buffer_bytes: AudioBufferBytes1;
  epoch: Epoch6;
  last_input_seq?: LastInputSeq1;
  last_output_seq?: LastOutputSeq1;
  lease_id: LeaseId6;
  message_id: MessageId8;
  observed_at: ObservedAt1;
  protocol: Protocol8;
  protocol_minor: ProtocolMinor8;
  sent_at: SentAt8;
  seq: Seq1;
  session_id: SessionId6;
  state: State1;
  type: Type8;
}
export interface WorkerStatsV1 {
  epoch: Epoch7;
  lease_id: LeaseId7;
  message_id: MessageId9;
  processed_audio_ms: ProcessedAudioMs;
  protocol: Protocol9;
  protocol_minor: ProtocolMinor9;
  realtime_factor: RealtimeFactor;
  revision: Revision3;
  segments_accepted: SegmentsAccepted;
  segments_rejected: SegmentsRejected;
  sent_at: SentAt9;
  seq: Seq2;
  session_id: SessionId7;
  stats_id: StatsId;
  type: Type9;
  window_ended_at: WindowEndedAt;
  window_started_at: WindowStartedAt;
}
export interface WorkerStatsV1Minor1 {
  epoch: Epoch8;
  lease_id: LeaseId8;
  message_id: MessageId10;
  processed_audio_ms: ProcessedAudioMs1;
  protocol: Protocol10;
  protocol_minor: ProtocolMinor10;
  realtime_factor: RealtimeFactor1;
  revision: Revision4;
  segments_accepted: SegmentsAccepted1;
  segments_rejected: SegmentsRejected1;
  sent_at: SentAt10;
  seq: Seq3;
  session_id: SessionId8;
  stats_id: StatsId1;
  type: Type10;
  window_ended_at: WindowEndedAt1;
  window_started_at: WindowStartedAt1;
}
export interface TranscriptSegmentV1 {
  confidence?: Confidence;
  end_ms: EndMs;
  epoch: Epoch9;
  is_final: IsFinal;
  language?: Language;
  lease_id: LeaseId9;
  message_id: MessageId11;
  protocol: Protocol11;
  protocol_minor: ProtocolMinor11;
  revision: Revision5;
  segment_id: SegmentId;
  sent_at: SentAt11;
  seq: Seq4;
  session_id: SessionId9;
  start_ms: StartMs;
  text: Text;
  type: Type11;
}
export interface TranscriptSegmentV1Minor1 {
  confidence?: Confidence1;
  end_ms: EndMs1;
  epoch: Epoch10;
  is_final: IsFinal1;
  language?: Language1;
  lease_id: LeaseId10;
  message_id: MessageId12;
  protocol: Protocol12;
  protocol_minor: ProtocolMinor12;
  revision: Revision6;
  segment_id: SegmentId1;
  sent_at: SentAt12;
  seq: Seq5;
  session_id: SessionId10;
  start_ms: StartMs1;
  text: Text1;
  type: Type12;
}
export interface TimelineEventV1 {
  epoch: Epoch11;
  event_id: EventId;
  message_id: MessageId13;
  occurred_at: OccurredAt;
  payload: Payload;
  protocol: Protocol13;
  protocol_minor: ProtocolMinor13;
  revision: Revision7;
  room_id: RoomId2;
  sent_at: SentAt13;
  seq: Seq6;
  session_id: SessionId11;
  type: Type13;
}
export interface TranscriptTimelinePayloadV1 {
  confidence?: Confidence2;
  end_ms: EndMs2;
  is_final: IsFinal2;
  language?: Language2;
  segment_id: SegmentId2;
  start_ms: StartMs2;
  text: Text2;
}
export interface SessionStatusTimelinePayloadV1 {
  reason_code?: ReasonCode;
  status: Status;
}
export interface TimelineEventV1Minor1 {
  epoch: Epoch12;
  event_id: EventId1;
  message_id: MessageId14;
  occurred_at: OccurredAt1;
  payload: Payload1;
  protocol: Protocol14;
  protocol_minor: ProtocolMinor14;
  revision: Revision8;
  room_id: RoomId3;
  sent_at: SentAt14;
  seq: Seq7;
  session_id: SessionId12;
  type: Type14;
}
export interface ViewerSubscribeV1 {
  client_version: ClientVersion;
  cursor?: ViewerCursorV1 | null;
  message_id: MessageId15;
  protocol: Protocol15;
  protocol_minor: ProtocolMinor15;
  room_id: RoomId4;
  sent_at: SentAt15;
  supported_minors: SupportedMinors1;
  type: Type15;
}
export interface ViewerCursorV1 {
  epoch: Epoch13;
  next_seq: NextSeq;
  session_id: SessionId13;
}
export interface ViewerReadyV1 {
  cursor_resumed: CursorResumed;
  epoch: Epoch14;
  message_id: MessageId16;
  minimum_client_version: MinimumClientVersion;
  next_seq: NextSeq1;
  protocol: Protocol16;
  protocol_minor: ProtocolMinor16;
  selected_minor: SelectedMinor2;
  sent_at: SentAt16;
  session_id: SessionId14;
  type: Type16;
}
export interface ViewerReadyV1Minor1 {
  cursor_resumed: CursorResumed1;
  epoch: Epoch15;
  message_id: MessageId17;
  minimum_client_version: MinimumClientVersion1;
  next_seq: NextSeq2;
  protocol: Protocol17;
  protocol_minor: ProtocolMinor17;
  selected_minor: SelectedMinor3;
  sent_at: SentAt17;
  session_id: SessionId15;
  type: Type17;
}
export interface ProtocolAckV1 {
  acknowledged_message_id: AcknowledgedMessageId;
  expected_revision?: ExpectedRevision2;
  message_id: MessageId18;
  outcome: Outcome;
  protocol: Protocol18;
  protocol_minor: ProtocolMinor18;
  revision?: Revision9;
  sent_at: SentAt18;
  seq?: Seq8;
  type: Type18;
}
export interface ProtocolAckV1Minor1 {
  acknowledged_message_id: AcknowledgedMessageId1;
  expected_revision?: ExpectedRevision3;
  message_id: MessageId19;
  outcome: Outcome1;
  protocol: Protocol19;
  protocol_minor: ProtocolMinor19;
  revision?: Revision10;
  sent_at: SentAt19;
  seq?: Seq9;
  type: Type19;
}
export interface ProtocolErrorV1 {
  code: Code;
  expected?: Expected;
  message: Message;
  message_id: MessageId20;
  protocol: Protocol20;
  protocol_minor: ProtocolMinor20;
  received?: Received;
  retryable: Retryable;
  sent_at: SentAt20;
  type: Type20;
}
export interface ProtocolErrorV1Minor1 {
  code: Code1;
  expected?: Expected1;
  message: Message1;
  message_id: MessageId21;
  protocol: Protocol21;
  protocol_minor: ProtocolMinor21;
  received?: Received1;
  retryable: Retryable1;
  sent_at: SentAt21;
  type: Type21;
}
export interface EpochRotatedV1 {
  closed_epoch: ClosedEpoch;
  lease_id: LeaseId11;
  media_continue_ms: MediaContinueMs;
  message_id: MessageId22;
  opened_epoch: OpenedEpoch;
  pcm_continue_pts: PcmContinuePts;
  protocol: Protocol22;
  protocol_minor: ProtocolMinor22;
  reason: Reason2;
  sent_at: SentAt22;
  session_id: SessionId16;
  type: Type22;
}
export interface ViewerResyncV1 {
  epoch: Epoch16;
  gap: Gap;
  media_continue_ms: MediaContinueMs1;
  message_id: MessageId23;
  next_seq: NextSeq3;
  protocol: Protocol23;
  protocol_minor: ProtocolMinor23;
  reason: Reason3;
  room_id: RoomId5;
  sent_at: SentAt23;
  session_id: SessionId17;
  type: Type23;
}
