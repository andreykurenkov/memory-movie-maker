# ADR-001: Use Google ADK for Multi-Agent Orchestration

Date: 2025-08-02
Status: Accepted

## Context

Memory Movie Maker requires orchestration of multiple AI components (analysis, composition, evaluation, refinement) to create videos. We need a framework that:

1. Supports multi-agent architectures
2. Provides agent communication patterns
3. Integrates well with Google's AI services (Gemini)
4. Offers good developer experience
5. Scales from local to cloud deployment

## Decision

We will use Google's Agent Development Kit (ADK) as our primary framework for building the multi-agent system.

## Consequences

### Positive

- **Native Gemini Integration**: ADK is optimized for Google's AI services, providing seamless integration with Gemini API
- **Multi-Agent Support**: Built-in patterns for agent orchestration (Sequential, Parallel, Loop agents)
- **Developer Experience**: Code-first approach with Python, familiar patterns, good documentation
- **Deployment Flexibility**: Can run locally for MVP and scale to Vertex AI for production
- **Tool Ecosystem**: Rich set of pre-built tools and easy custom tool creation
- **Testing Support**: Built-in testing utilities for agents

### Negative

- **Lock-in Risk**: Tied to Google's ecosystem, though ADK claims to be model-agnostic
- **Learning Curve**: Team needs to learn ADK patterns and best practices
- **Maturity**: Relatively new framework (as of 2025), may have undiscovered issues
- **Documentation**: While good, not as extensive as more established frameworks

### Neutral

- **Performance**: Depends on underlying model calls, not significantly different from alternatives
- **Cost**: Similar to other LLM orchestration approaches

## Alternatives Considered

### 1. LangChain
- **Pros**: More mature, larger community, extensive integrations
- **Cons**: More complex, less optimized for multi-agent systems, heavier framework

### 2. Custom Orchestration
- **Pros**: Full control, no dependencies, tailored to our needs
- **Cons**: Significant development effort, need to solve solved problems, maintenance burden

### 3. AutoGen (Microsoft)
- **Pros**: Good multi-agent support, conversation patterns
- **Cons**: Less integrated with Google services, different paradigm

## Implementation Notes

1. Start with ADK's `LlmAgent` base class for all agents
2. Use `SequentialAgent` for the main orchestration flow
3. Leverage built-in tools where possible, create custom tools for domain-specific needs
4. Follow ADK's testing patterns for unit and integration tests
5. Plan for potential migration by keeping business logic separate from ADK-specific code

## References

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [ADK GitHub Repository](https://github.com/google/adk-python)
- [Comparison of AI Agent Frameworks (2025)](https://example.com/ai-frameworks-comparison)