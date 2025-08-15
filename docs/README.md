# Documentation Index

This directory contains comprehensive documentation for the Memory Movie Maker project. Start here to understand the system architecture, APIs, and development workflows.

## Quick Navigation

### 🚀 Getting Started
- **[../README.md](../README.md)** - Project overview, installation, and usage examples
- **[../CLAUDE.md](../CLAUDE.md)** - Complete developer guide and project context

### 🏗️ Architecture & Design
- **[AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md)** - In-depth multi-agent system design
- **[TDD.md](TDD.md)** - Technical design document and project structure
- **[API_REFERENCE.md](API_REFERENCE.md)** - Comprehensive API documentation

### 🤖 Agent Workflows
- **[ROOT_AGENT_GUIDE.md](ROOT_AGENT_GUIDE.md)** - RootAgent orchestration and workflow details

### 📈 Project Management
- **[roadmap.md](roadmap.md)** - Development progress and future plans

### 📋 Decision Records
- **[adr/](adr/)** - Architecture Decision Records (ADRs)
  - [001-use-google-adk.md](adr/001-use-google-adk.md) - Why we chose Google ADK
  - [002-data-model-design.md](adr/002-data-model-design.md) - Data model design decisions

## Documentation Overview

### For New Developers

If you're new to the project, read in this order:

1. **[../README.md](../README.md)** - Understand what the project does and how to run it
2. **[../CLAUDE.md](../CLAUDE.md)** - Get complete development context
3. **[AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md)** - Learn the multi-agent system design
4. **[API_REFERENCE.md](API_REFERENCE.md)** - Understand the data models and APIs

### For API Integration

If you want to integrate with or extend the system:

1. **[API_REFERENCE.md](API_REFERENCE.md)** - Complete API documentation
2. **[AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md)** - Agent interaction patterns
3. **[TDD.md](TDD.md)** - Technical implementation details

### For System Understanding

If you want to understand how the system works internally:

1. **[AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md)** - Multi-agent orchestration
2. **[ROOT_AGENT_GUIDE.md](ROOT_AGENT_GUIDE.md)** - Workflow coordination
3. **[adr/](adr/)** - Key architectural decisions

## Key Concepts

### Multi-Agent Architecture
The system uses **5 specialized agents** orchestrated by a central RootAgent:
- **AnalysisAgent**: Media content understanding
- **CompositionAgent**: AI-powered video creation  
- **EvaluationAgent**: Quality assessment
- **RefinementAgent**: Feedback interpretation
- **RootAgent**: Workflow orchestration

### Hybrid AI Approach
The system combines **3 complementary AI techniques**:
- **Technical Analysis** (Librosa): Beat detection, tempo mapping
- **Semantic Understanding** (Gemini): Content comprehension, story structure
- **Creative Synthesis** (Gemini): Intelligent edit planning

### Self-Correction Loop
Videos are automatically improved through iterative refinement:
1. Generate initial video
2. Evaluate quality (target: ≥7.0/10)
3. Apply AI-generated improvements if needed
4. Re-render and re-evaluate (up to 3 iterations)

## Technology Stack

### Core Technologies
- **Google ADK**: Multi-agent orchestration framework
- **Gemini API**: Visual analysis and edit planning AI
- **Librosa**: Professional audio analysis (beats, musical structure)
- **MoviePy**: Video rendering and effects
- **Gradio**: Modern web interface

### Development Tools
- **Python 3.10+**: Primary language with type hints
- **Pydantic**: Data validation and serialization
- **Pytest**: Comprehensive testing framework
- **Black/isort/mypy**: Code quality tools

## Project Structure

```
memory-movie-maker/
├── src/memory_movie_maker/     # Main package
│   ├── agents/                 # Multi-agent system
│   ├── tools/                  # Agent capabilities
│   ├── models/                 # Data models
│   ├── storage/                # Storage abstraction
│   └── web/                    # Web interface
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── scripts/                    # Development utilities
├── docs/                       # Documentation (this directory)
└── test_inputs/                # Test media files
```

## Contributing

When adding new documentation:

1. **Update this index** - Add your new document to the appropriate section
2. **Follow the structure** - Use consistent formatting and organization
3. **Link references** - Cross-reference related documents
4. **Include examples** - Provide practical code examples where relevant
5. **Keep it current** - Update docs when code changes

## Documentation Standards

- **Use clear headings** - Make documents scannable
- **Provide context** - Explain why, not just what
- **Include examples** - Show practical usage
- **Cross-reference** - Link to related concepts
- **Keep updated** - Docs should match current implementation

## Questions?

For questions about the documentation or system:

1. Check the relevant documentation section first
2. Look at code examples in the **[API_REFERENCE.md](API_REFERENCE.md)**
3. Review architectural decisions in **[adr/](adr/)**
4. Check the project's README for troubleshooting tips

The documentation is designed to be comprehensive and self-contained. Each document serves a specific purpose and audience, so start with the document that best matches your needs.