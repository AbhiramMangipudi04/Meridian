"""Nexus Data module.

This package contains everything the capstone's "Data module" is
responsible for: SQLAlchemy models, domain-scoped repositories, the
access-control layer that enforces server/table boundaries, deterministic
seed data, and the unstructured knowledge-base documents.

Nothing in this package implements MCP servers, agents, retrieval, or LLM
logic. It is a foundation the future server layer will consume.
"""
