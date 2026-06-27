# LLM provider abstraction: dual local and hosted open-source-model backends

The product must use open-source model weights without lock-in to a proprietary paid LLM,
while still allowing convenient hosted inference when desired. The PRD requires that the
system always remain fully runnable locally at zero mandatory cost.

## Status

Accepted.

## Considered Options

- **Pluggable provider abstraction with two interchangeable backends — a local runtime
  (Ollama or vLLM) and hosted providers that serve open-source models, e.g. Groq
  (chosen)**: no mandatory dependency on any single provider, and the system always
  remains fully runnable in local-only mode.
- **Local-only (Ollama or vLLM)**: rejected — forgoes the convenience and throughput of
  hosted open-source inference (e.g., Groq) when the user wants it.
- **Hosted-only or proprietary closed-model API**: rejected — violates the
  open-source-weights and no-mandatory-paid-dependency constraints and creates vendor
  lock-in.

## Consequences

- The implementation introduces an LLM client interface with swappable backends in Phase
  4; nothing LLM-related is built in Phase 0.
- All agent outputs are validated against schemas with retries regardless of the backend,
  per the PRD.
- Local-only mode remains a first-class, zero-cost configuration.
- Which specific local runtime and which hosted provider(s) ship in the initial setup
  remains an open question in the PRD, to be fixed when the LLM layer is specced.
