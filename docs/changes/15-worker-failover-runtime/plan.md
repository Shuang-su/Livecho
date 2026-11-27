# Implementation plan: Connect the scheduler and viewer to minor 1

1. Review and merge the corrected #14 gateway contract, then implement and
   verify its bound upgrade and single-lease foundation. Merge this #15
   artifact before changing an application runtime. Retain #5 model and host
   evidence as the qualification gate. Use only synthetic observations
   before that qualification.
2. Introduce one session owner in the backend. Wire eligible sockets,
   scheduler state and the approved allowlist to the #27 protocol adapter.
   Pass validated worker envelopes and PCM header metadata to the adapter.
   Keep PCM transport and queue ownership in the existing #8/#14 boundary.
   Verify no bypass of signature admission on reconnect.
3. Serialize lease promotion and viewer fan-out around one rotation result.
   Fence writes to the closed lease, flush or drop only according to accepted
   bounds, and use the returned wire notices. Record the chosen steady-state
   lease continuation policy along with the synthetic fault contract.
4. In the owning viewer/worker change, enable minor 1 only when the peer
   can consume the existing closed twins and resync behavior with no downgrade
   or body replay. Cover cleanup of queued old-epoch browser output. If a
   consumer change belongs to a distinct Issue, merge its artifacts first.
5. Run deterministic protocol and existing minor-0 tests before the controlled
   three-worker run. Record exact commands, accepted frames and stable codes,
   time-to-first-final, queue bounds and gap duration under this Issue.
   Keep the 8-hour real-clock run and accelerated rotations as separate #19
   evidence once the integration and host gates support those tests.

## Rollout and rollback

Start on a controlled loopback synthetic service with the old minor-0 fixture
available separately. An untested or incompatible subscriber fails closed.
Rollback stops the minor-1 session and clears controller, lease, PCM and
viewer state. The old session and its retired epochs cannot resume. No
credential provisioning, real-source enablement, or deployment is part of
this local artifact.

## Open decisions

Owner acceptance of bounded healthy-lease continuation and its gap budget is
required before measuring sustained operation. A design that needs renewable
expiry, new fields or a different transition is a protocol proposal, not an
implementation shortcut.
