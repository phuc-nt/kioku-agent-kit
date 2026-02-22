# Multi-Tenant & Identity Mapping Strategy (Cloud Scale)

**Date:** 2026-02-22  
**Status:** Proposed Architecture  
**Context:** The current MVP isolates tenants using the `KIOKU_USER_ID` environment variable at startup. This works for single-user endpoints or containerized deployments where one process serves one tenant. Moving to a unified Cloud/SaaS deployment where multiple users (and multiple devices per user) access a single MCP Server requires a scalable identity strategy.

---

## 🛑 The Problem: Omnichannel Identity Fragmentation
When a single human user interacts with Kioku through multiple channels:
- Telegram Bot A (Home/Personal)
- Telegram Bot B (Work)
- Discord (Community)
- Web App / CLI

The MCP Server must recognize that these disparate **Channel IDs** mapping to the same human should share the same core memory spaces (Vector DB, Knowledge Graph, Markdown storage), without exposing data to other users.

---

## 🛠 Proposed Solutions (From MVP to Enterprise)

### Phase 1: Request-Level Context Injection (Next Step)
Currently, `config.py` loads `KIOKU_USER_ID` once. To support a multi-tenant process, the identity must be parsed per-request.

**Implementation:**
- Move away from initializing global storage clients at module load time (`server.py`).
- Modify the MCP Server wrapper (FastMCP) or tools to extract contextual metadata from the MCP protocol headers/RequestContext.
- Dynamically select the correct ChromaDB collection (`memories_UUID`) and FalkorDB graph (`kioku_kg_UUID`) at execution time based on the active request's context.

### Phase 2: Identity Mapping Middleware (Omnichannel)
A single user needs to link multiple "channels" to one "brain."

**Implementation:**
1. **Database Schema (PostgreSQL/Redis):**
   - `kioku_uid`: *uuid* (e.g., `kioku_1a2b3c...`)
   - `channel_type`: *string* (e.g., `telegram`, `discord`, `web`)
   - `channel_uid`: *string* (e.g., Telegram User ID `12345678`)
2. **Flow:**
   - A request arrives with a payload indicating `telegram:12345678`.
   - The Identity Middleware queries the mapping DB: `SELECT kioku_uid FROM link WHERE channel_uid='12345678'`.
   - The request is routed to the underlying stores using `kioku_uid`.
3. **Account Linking:**
   - Implement an MCP tool or CLI command `/link_account`.
   - A user asks their primary bot for a one-time OTP and submits it to their secondary bot, linking the `channel_uid` to the primary `kioku_uid`.

### Phase 3: Centralized Identity Management (IAM / OAuth2)
For an Enterprise SaaS or large-scale rollout (e.g., Brain Communications Dev Branch).

**Implementation:**
- Offload registration and authentication to an external provider (Auth0, Clerk, Firebase).
- Users authenticate out-of-band (e.g., via a secure web portal linked from the bot).
- The Auth Provider issues a JWT (JSON Web Token) to the bot/client.
- OpenClaw or the connecting Agent system injects the `Bearer JWT` into the MCP Transport layer (SSE or WebSocket headers).
- Kioku MCP Server validates the JWT signature, extracts the definitive `tenant_id`, and safely scopes all data access.

---

## 🚀 Action Items
- [ ] Refactor `config.py` and `server.py` to allow dependency injection of storage clients per-request rather than relying on global singletons.
- [ ] Investigate if `FastMCP` exposes arbitrary transport headers or allows custom `Context` dependencies in tool decorators.
- [ ] Define the schema for the `user_mapping` table (can be built within FalkorDB or a lightweight SQLite DB initially).
