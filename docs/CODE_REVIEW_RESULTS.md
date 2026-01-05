# LanComm Code Review Snapshot (Updated)
**Date**: January 5, 2026  
**Scope**: server.py + beltpack.py at current branch state

---

## ✅ Current State
- Ports: TCP/UDP 6001 on both sides; QoS DSCP AF41 marking applied when allowed by OS.
- Limits: MAX_CHANNELS=10; MAX_USER_CHANNELS=4; MAX_USERS=20; JITTER_BUFFER_SIZE=6; CHUNK=960.
- Auth: SHA-256 challenge/response using shared `AUTH_KEY`.
- Discovery: Server advertises `_lancomm._tcp.local`; beltpack discovers with 10s timeout then falls back to `SERVER_HOST`.
- UDP formats: Uplink `[ch][user_id][seq][pcm16]`; downlink `[ch][zeros][pcm16]`.
- Null routing: Server excludes each listener’s own audio; beltpack sidetone is local-only.
- 4-wire: Two bridges with per-interface gain and channel selection; restart on config change; null-routed to avoid feedback.

---

## 🔧 Recent Fixes (key items)
- Beltpack uplink now targets the negotiated server address and binds UDP before advertising `SET_UDP`, preventing port 0/incorrect target issues.
- Audio mixer on beltpack cleaned of stray async code; per-channel volume application restored.
- Channel disable on server now drops listeners/talkers/buffers immediately.
- mDNS discovery path hardened with timeout + fallback.

---

## ⚠️ Known Gaps / Follow-Ups
- VOX exists but is a manual code toggle; no GUI control and uses a single gate path today.
- Hardware polling assumes four physical RGB buttons (matches MAX_USER_CHANNELS=4); expansion beyond 4 buttons would need code changes.
- Link-local addressing not implemented; relies on DHCP/static + mDNS.
- PyAudio instance is module-level; ensure `p` is closed on shutdown (best-effort today).

---

## 🧪 Test Focus
- End-to-end audio: multi-talker mixing on a channel; confirm null routing (talkers do not hear themselves) and sidetone remains local.
- Discovery: mDNS on a multicast-allowed LAN; verify fallback to `SERVER_HOST` works when blocked.
- Auth failure path: mismatched `AUTH_KEY` should return `AUTH_FAIL` and drop connection.
- 4-wire bridges: enable each interface, verify gain direction and that its own input is nulled from its output.

---

## Deployment Notes
- Run server with admin privileges when possible to allow DSCP marking; otherwise switch-side QoS trust is sufficient.
- Keep `AUTH_KEY` in sync before packaging with PyInstaller.
- For production, keep per-user channel assignments ≤4 (matches hardware buttons and enforced in UI).

This replaces earlier, line-numbered review notes and reflects the current codebase as of January 5, 2026.
