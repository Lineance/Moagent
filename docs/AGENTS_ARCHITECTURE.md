# MoAgent System Architecture

This document provides a detailed explanation of the agent system architecture in MoAgent.

## Overview

MoAgent uses a sophisticated multi-agent architecture that combines:

1. **LangGraph-based workflow orchestration** for high-level coordination
2. **Multi-agent collaboration** for complex task decomposition
3. **RAG-enhanced pattern learning** for intelligent web crawling
4. **Automatic pattern generation** for adapting to new websites

```
┌─────────────────────────────────────────────────────────────┐
│                    MoAgent System                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Coordinator Agent (LangGraph)               │    │
│  │  - Workflow orchestration                           │    │
│  │  - State management                                │    │
│  │  - Conditional routing                              │    │
│  │  - Error recovery                                   │    │
│  └──────────┬──────────────────────────────────┬───────┘    │
│             │                                  │              │
│             ▼                                  ▼              │
│  ┌─────────────────────┐          ┌──────────────────────┐  │
│  │  RAG Coordinator    │          │  Multi-Agent System  │  │
│  │  - Pattern learning │          │  - Supervisor        │  │
│  │  - Vector storage   │          │  - Explorer          │  │
│  │  - Knowledge base   │          │  - Analyst           │  │
│  └──────────┬──────────┘          │  - Optimizer         │  │
│             │                     │  - Validator         │  │
│             ▼                     └──────────┬───────────┘  │
│  ┌─────────────────────┐                      │            │
│  │ Pattern Generator   │                      │            │
│  │ - Rule-based        │                      │            │
│  │ - LLM-powered       │                      │            │
│  │ - Refinement        │                      │            │
│  └─────────────────────┘                      │            │
│                                                │            │
└────────────────────────────────────────────────┼────────────┘
                                                 │
                                                 ▼
                                    ┌──────────────────────┐
                                    │  Crawling Pipeline   │
                                    │  - Crawlers          │
                                    │  - Parsers           │
                                    │  - Storage           │
                                    └──────────────────────┘
```

## 1. Coordinator Agent

**File**: `moagent/agents/coordinator.py`

The Coordinator Agent is the main orchestrator using LangGraph for workflow management.

### Responsibilities

- **Workflow Orchestration**: Manages the end-to-end crawling pipeline
- **State Management**: Maintains workflow state across multiple stages
- **Conditional Routing**: Routes data based on processing results
- **Error Recovery**: Handles failures with fallback strategies

### State Management

```python
class AgentState(TypedDict):
    """State for the LangGraph workflow."""
    config: Config
    phase: str  # 'init', 'crawling', 'parsing', 'storage'
    raw_data: List[Dict[str, Any]]
    parsed_data: List[Dict[str, Any]]
    new_items: List[Dict[str, Any]]
    errors: List[str]
```

### Workflow Stages

1. **Initialization**: Setup configuration and validate environment
2. **Crawling**: Fetch raw data from target URLs
3. **Parsing**: Extract structured content from raw data
4. **Storage**: Persist processed data to database
5. **Completion**: Return results and cleanup

## 2. RAG Coordinator

**File**: `moagent/agents/rag_coordinator.py`

Integrates Retrieval Augmented Generation for intelligent pattern learning.

### Key Features

- **Vector Storage**: Stores patterns as embeddings in ChromaDB
- **Pattern Retrieval**: Finds similar patterns from past crawls
- **Knowledge Base**: Learns from successful extractions
- **Semantic Search**: Uses embeddings to find relevant patterns

### Components

```
RAG Coordinator
├── EmbeddingGenerator  # Create embeddings for patterns
├── VectorStore         # ChromaDB for vector storage
├── Retriever           # Semantic pattern search
└── KnowledgeBase       # Pattern management
```

### Workflow

```
┌──────────────┐
│ New URL to   │
│   Crawl      │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Generate Vector  │
│   Embedding      │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Search Similar   │
│   Patterns       │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Apply Best       │
│   Pattern        │
└──────────────────┘
```

## 3. Multi-Agent System

**Directory**: `moagent/agents/multi_agent/`

A sophisticated multi-agent collaboration system for complex task decomposition.

### Architecture

```
┌──────────────────────────────────────────────────┐
│           Multi-Agent System                     │
├──────────────────────────────────────────────────┤
│                                                   │
│  ┌────────────────────────────────────────┐     │
│  │       Supervisor Agent                 │     │
│  │  - Task decomposition                  │     │
│  │  - Agent scheduling                    │     │
│  │  - Result aggregation                  │     │
│  └──┬─────┬──────┬──────┬──────┬─────────┘     │
│     │     │      │      │      │               │
│     ▼     ▼      ▼      ▼      ▼               │
│  ┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐    │
│  │Explorer│Analyst│Optimizer│Validator│         │
│  └──────┘└──────┘└──────┘└──────┘└──────┘    │
│                                                   │
└──────────────────────────────────────────────────┘
```

### 3.1 Base Agent

**File**: `moagent/agents/multi_agent/base.py`

Abstract base class defining the core agent interface.

#### Key Classes

```python
class AgentStatus(Enum):
    """Agent状态枚举"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"

@dataclass
class Task:
    """任务定义"""
    task_id: str
    task_type: str
    params: Dict[str, Any]
    priority: int = 5
    timeout: Optional[int] = None
    depends_on: List[str] = field(default_factory=list)
```

#### Agent Lifecycle

1. **Initialize**: Setup agent configuration and capabilities
2. **Receive Task**: Accept task from supervisor
3. **Execute**: Perform task with retry logic
4. **Report**: Return results to supervisor
5. **Cleanup**: Release resources

### 3.2 Supervisor Agent

**File**: `moagent/agents/multi_agent/agents/supervisor.py`

Central coordinator for multi-agent workflows.

#### Responsibilities

1. **Task Decomposition**: Break complex tasks into sub-tasks
2. **Agent Allocation**: Assign tasks to appropriate agents
3. **Execution Monitoring**: Track progress and handle timeouts
4. **Exception Handling**: Retry failed tasks or delegate
5. **Result Aggregation**: Combine results from multiple agents

#### Workflow

```python
# Example supervisor workflow
task = Task(
    task_id="crawl_complex_site",
    task_type="multi_step_crawling",
    params={"url": "https://example.com"}
)

# Supervisor decomposes task:
subtasks = [
    Task(task_id="explore", task_type="exploration", ...),
    Task(task_id="analyze", task_type="analysis", ...),
    Task(task_id="optimize", task_type="optimization", ...),
    Task(task_id="validate", task_type="validation", ...)
]

# Assign to specialized agents
explorer_agent.execute(subtasks[0])
analyst_agent.execute(subtasks[1])
optimizer_agent.execute(subtasks[2])
validator_agent.execute(subtasks[3])

# Aggregate results
final_result = supervisor.aggregate_results()
```

### 3.3 Specialized Agents

#### Explorer Agent

**File**: `moagent/agents/multi_agent/agents/explorer.py`

**Role**: Web exploration and discovery

**Capabilities**:
- Discover website structure
- Identify list pages and content pages
- Find pagination patterns
- Detect navigation menus
- Map site architecture

**Use Case**: First pass at a new website to understand structure

#### Analyst Agent

**File**: `moagent/agents/multi_agent/agents/analyst.py`

**Role**: Data analysis and extraction

**Capabilities**:
- Analyze HTML structure
- Extract content patterns
- Identify data fields
- Detect content relationships
- Generate extraction rules

**Use Case**: Deep analysis of page structure for pattern generation

#### Optimizer Agent

**File**: `moagent/agents/multi_agent/agents/optimizer.py`

**Role**: Performance optimization

**Capabilities**:
- Optimize crawl strategies
- Adjust concurrency levels
- Cache frequently accessed data
- Minimize API calls
- Reduce bandwidth usage

**Use Case**: Continuous improvement of crawling efficiency

#### Validator Agent

**File**: `moagent/agents/multi_agent/agents/validator.py`

**Role**: Result validation and quality assurance

**Capabilities**:
- Validate extracted data
- Check data completeness
- Detect anomalies
- Ensure data consistency
- Quality scoring

**Use Case**: Final validation before storage

### 3.4 Agent Communication

**File**: `moagent/agents/multi_agent/communication.py`

Inter-agent communication system using message passing.

#### Message Types

```python
@dataclass
class AgentMessage:
    """Agent message"""
    sender: str
    receiver: str
    message_type: str  # 'task', 'result', 'status', 'error'
    content: Dict[str, Any]
    timestamp: datetime
    correlation_id: str
```

#### Communication Patterns

1. **Task Assignment**: Supervisor → Worker Agent
2. **Status Update**: Worker Agent → Supervisor
3. **Result Reporting**: Worker Agent → Supervisor
4. **Error Notification**: Any Agent → Supervisor
5. **Agent-to-Agent**: Direct communication when needed

### 3.5 Workflow Management

**Directory**: `moagent/agents/multi_agent/workflow/`

#### Graph-based Workflow

**File**: `moagent/agents/multi_agent/workflow/graph.py`

LangGraph-based workflow definition for complex agent coordination.

**Features**:
- Directed acyclic graph (DAG) of agent tasks
- Parallel execution of independent tasks
- Dependency management
- State tracking across workflow

#### Adaptive Workflow

**File**: `moagent/agents/multi_agent/workflow/adaptive.py`

Dynamic workflow adaptation based on execution results.

**Features**:
- Real-time workflow adjustment
- Error recovery with alternative paths
- Performance-based optimization
- Learning from past executions

## 4. Pattern Generator

**Directory**: `moagent/agents/pattern_generator/`

Automatic pattern generation for adapting to new websites.

### Components

```
Pattern Generator System
├── Basic List Pattern Generator  # Rule-based generation
├── HTML Downloader               # Fetch HTML for analysis
├── LLM Pattern Generator         # LLM-powered generation
├── LLM Pattern Comparator        # Compare multiple patterns
└── LLM Pattern Refiner           # Refine patterns with feedback
```

### 4.1 Basic Pattern Generator

**File**: `moagent/agents/pattern_generator/basic_list_pattern_generator.py`

Rule-based pattern generation without LLM.

**Algorithm**:
1. Analyze HTML structure
2. Identify repeating elements
3. Generate CSS selectors
4. Validate with sample data
5. Score pattern confidence

**Output**:
```yaml
list_container:
  tag: "ul"
  class: "news-list"
list_item:
  tag: "li"
title:
  selector: "h2.title"
link:
  selector: "a.link"
  attribute: "href"
```

### 4.2 LLM Pattern Generator

**File**: `moagent/agents/pattern_generator/llm_pattern_generator.py`

LLM-powered semantic pattern understanding.

**Process**:
1. Download sample HTML
2. Send to LLM with analysis prompt
3. Extract structured pattern
4. Validate with test data
5. Return confidence score

**Advantages**:
- Understands page semantics
- Handles complex structures
- Adapts to new patterns
- Provides reasoning

**Output**:
```python
@dataclass
class LLMPatternAnalysis:
    list_container: Dict[str, Any]
    item_selector: Dict[str, Any]
    title_selector: Dict[str, Any]
    url_selector: Dict[str, Any]
    date_selector: Optional[Dict[str, Any]]
    content_selector: Optional[Dict[str, Any]]
    post_process: Dict[str, Any]
    confidence: float
    reasoning: str  # LLM explanation
```

### 4.3 Pattern Comparator

**File**: `moagent/agents/pattern_generator/llm_pattern_comparator.py`

Compare and evaluate multiple patterns.

**Metrics**:
- Coverage: How many items are extracted
- Accuracy: How accurate are the extractions
- Robustness: How well it handles variations
- Performance: How fast it executes

### 4.4 Pattern Refiner

**File**: `moagent/agents/pattern_generator/llm_pattern_refiner.py`

Iterative pattern improvement with feedback.

**Process**:
1. Test current pattern
2. Collect failure cases
3. Send to LLM with feedback
4. Generate refined pattern
5. Validate improvements
6. Repeat if needed

## 5. Integration with Crawling Pipeline

The agent system integrates with the crawling pipeline as follows:

```
┌───────────────────────────────────────────────────────┐
│                   Agent Layer                          │
│  - Coordinator orchestration                          │
│  - Multi-agent collaboration                          │
│  - Pattern generation & learning                      │
└───────────────┬───────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────┐
│                Crawling Layer                          │
│  - Crawlers (list, content, dynamic)                  │
│  - Parsers (generic, LLM, hybrid)                     │
└───────────────┬───────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────┐
│                Storage Layer                           │
│  - Database (SQLite, PostgreSQL)                      │
│  - Vector Store (ChromaDB)                            │
└───────────────────────────────────────────────────────┘
```

## 6. Usage Examples

### 6.1 Simple Coordinator Usage

```python
from moagent import Config, run_agent

config = Config(
    target_url="https://example.com/news",
    crawl_mode="auto"
)

result = run_agent(config)
print(f"Processed {result.items_processed} items")
```

### 6.2 Multi-Agent Collaboration

```python
from moagent.agents.multi_agent.agents import (
    SupervisorAgent,
    ExplorerAgent,
    AnalystAgent
)
from moagent.agents.multi_agent.base import Task, AgentConfig

# Create supervisor
supervisor = SupervisorAgent(
    config=AgentConfig(
        agent_id="supervisor_1",
        role="supervisor",
        capabilities=["task_decomposition", "coordination"]
    )
)

# Define complex task
task = Task(
    task_id="complex_crawl",
    task_type="multi_step",
    params={"url": "https://example.com"}
)

# Execute with multi-agent collaboration
result = supervisor.execute(task)
```

### 6.3 Pattern Generation

```python
from moagent.agents.pattern_generator import LLMPatternGeneratorAgent

generator = LLMPatternGeneratorAgent(config=your_config)

# Generate pattern from URL
pattern = generator.generate_from_url("https://example.com/news")

# Save pattern
pattern.save("configs/patterns/example_com.yaml")
```

### 6.4 RAG-Enhanced Crawling

```python
from moagent.agents.rag_coordinator import RAGCoordinator

rag = RAGCoordinator(config=your_config)

# Crawl with pattern learning
result = rag.crawl_with_learning("https://example.com/news")

# Pattern is automatically learned and stored for future use
```

## 7. Best Practices

### 7.1 Agent Design

- **Single Responsibility**: Each agent has a clear, focused role
- **Stateless**: Prefer stateless agents for easier scaling
- **Error Handling**: Always handle timeouts and failures
- **Logging**: Log important events for debugging

### 7.2 Workflow Design

- **Decomposition**: Break complex tasks into simple sub-tasks
- **Parallelism**: Execute independent tasks in parallel
- **Dependencies**: Clearly define task dependencies
- **Rollback**: Provide rollback mechanisms for failures

### 7.3 Pattern Management

- **Versioning**: Keep version history of patterns
- **Testing**: Always test patterns before deployment
- **Monitoring**: Monitor pattern performance
- **Refinement**: Continuously refine based on feedback

## 8. Troubleshooting

### Agent Stuck in BUSY State

```python
# Check agent status
status = agent.get_status()
if status == AgentStatus.BUSY:
    agent.timeout()  # Force timeout
```

### Pattern Generation Fails

```python
# Try rule-based fallback
try:
    pattern = llm_generator.generate(url)
except Exception:
    pattern = basic_generator.generate(url)
```

### Multi-Agent Communication Issues

```python
# Check communication channel
if not communication.is_healthy():
    communication.reset()
```

## 9. Future Enhancements

- [ ] Dynamic agent creation based on workload
- [ ] Cross-agent learning and knowledge sharing
- [ ] Distributed agent execution across machines
- [ ] Agent marketplace for community contributions
- [ ] Real-time monitoring dashboard
- [ ] Auto-tuning of agent parameters

## 10. References

- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- Multi-Agent Systems: https://en.wikipedia.org/wiki/Multi-agent_system
- RAG Architecture: https://arxiv.org/abs/2005.11401
