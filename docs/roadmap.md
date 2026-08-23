# Alpha roadmap

GitHub Issues are the canonical status. The sequence below defines dependency order; an
Issue may start only after its listed prerequisite artifacts are merged.

## M0 — repository and decisions

1. Repository and AI-native SDLC foundation.
2. Architecture ADR, threat model, data lifecycle, platform boundary, and AGPL isolation.
3. Protocol v1 source models, generated schemas/types, and golden compatibility fixtures.
4. Railway staging/production skeleton, private resources, migrations, health, and
   secret inventory.

## M1 — local real-time vertical

5. M3 Ultra MLX benchmark harness and model decision evidence.
6. MLX worker CLI and local-fixture transcription.
7. Public/free Bilibili room resolver and room state machine.
8. FFmpeg, VAD, bounded RAM audio buffer, reconnect, and no-persistence checks.
9. Single-worker end-to-end caption pipeline.
10. Danmaku, Super Chat, and live-status normalization and raw-event capture.
11. Public reconnecting live Web/PWA.

## M2 — distributed Alpha

12. Invite-only Resend magic-link authentication and roles.
13. Worker enrollment, device identity, model allowlist, health, and contribution stats.
14. Worker gateway, heartbeat, lease, epoch, expiry, and disconnect behavior.
15. Compatible-worker scheduling and failover.
16. Normalized Postgres timeline, encrypted raw archive, history, backup, takedown, and
    deletion.
17. Invited history, contributor statistics, and operator/admin console.
18. CUDA provider mock and cross-provider contract fixtures.
19. Railway production deployment, observability, recovery, and Alpha acceptance report.
