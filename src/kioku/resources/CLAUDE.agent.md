# Kioku Agent Guide

You are an AI assistant with access to **Kioku**, a long-term personal memory engine.
Kioku stores memories in a tri-hybrid index (BM25 keyword + semantic vector + knowledge graph).

Your primary task across all conversations is to proactively save important user context and recall it when necessary.

## Instructions
Do NOT attempt to guess how to use Kioku. All rules, commands, environment activation requirements, and setup verification steps are defined in the Kioku skill file.

**CRITICAL:** Before taking any action related to memory, searching, or saving, you MUST read the Kioku skill file for instructions:
- Read: `.claude/skills/kioku/SKILL.md`

Always follow the enrichment, safety, and environment isolation rules provided in the skill precisely!
