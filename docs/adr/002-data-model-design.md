# ADR-002: Centralized ProjectState Data Model

Date: 2025-08-02
Status: Accepted

## Context

In a multi-agent system, we need a way to:
1. Share data between agents
2. Track project evolution over time
3. Maintain consistency across operations
4. Enable debugging and monitoring
5. Support both synchronous and asynchronous operations

## Decision

We will use a single, centralized `ProjectState` object as the source of truth that flows through all agents. This state will be:
- Immutable between agent operations
- JSON-serializable
- Validated using Pydantic models
- Versioned for history tracking

## Consequences

### Positive

- **Simplicity**: One data structure to understand and maintain
- **Debugging**: Easy to inspect state at any point in the pipeline
- **Consistency**: All agents work with the same data structure
- **Persistence**: Can easily save/restore project state
- **Testing**: Simple to create test fixtures and assertions
- **Monitoring**: Can track state changes over time

### Negative

- **Size**: State object may become large with many media files
- **Performance**: Passing entire state between agents has overhead
- **Coupling**: All agents must understand the full state structure
- **Versioning**: Schema changes require careful migration

### Neutral

- **Flexibility**: Can add new fields without breaking existing agents
- **Type Safety**: Pydantic provides runtime validation

## Design Details

### Core Structure

```python
ProjectState = {
    "project_id": str,
    "created_at": datetime,
    "updated_at": datetime,
    
    "user_inputs": {
        "media": List[MediaAsset],
        "music": List[MediaAsset],
        "initial_prompt": str,
        "target_duration": int,
        "aspect_ratio": str,
        "style_preferences": Dict
    },
    
    "analysis": {
        "music_profiles": List[AudioProfile],
        "media_pool": List[EnrichedMediaAsset],
        "analysis_timestamp": datetime
    },
    
    "timeline": {
        "segments": List[TimelineSegment],
        "total_duration": float,
        "render_settings": Dict
    },
    
    "history": {
        "prompts": List[Dict],
        "versions": List[Dict],
        "feedback": List[Dict]
    },
    
    "status": {
        "phase": str,
        "progress": float,
        "current_version": int,
        "error": Optional[str]
    }
}
```

### Key Principles

1. **Append-Only History**: Never modify history, only append
2. **Explicit Phases**: Clear status.phase progression
3. **Error Containment**: Errors stored in state, not thrown
4. **Lazy Loading**: Media content not stored in state, only references

## Alternatives Considered

### 1. Message Passing
- Each agent sends specific messages to the next
- **Rejected**: Complex routing, harder to debug

### 2. Shared Database
- Agents read/write to a shared database
- **Rejected**: Adds complexity, concurrency issues

### 3. Event Sourcing
- Store all changes as events
- **Rejected**: Overkill for MVP, can migrate later if needed

## Migration Strategy

If we need to change the schema:
1. Add version field to ProjectState
2. Create migration functions between versions
3. Agents check version and migrate if needed
4. Gradual rollout with backward compatibility

## References

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Multi-Agent State Management Patterns](https://example.com/patterns)