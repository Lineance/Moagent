"""
Coordinator Agent - Manages the workflow orchestration using LangGraph.

This agent coordinates the crawling, parsing, and storage pipeline
using LangGraph for state management and workflow control.

Features:
- True LangGraph StateGraph implementation
- Conditional routing based on workflow state
- Error recovery with fallback paths
- Parallel processing support (future enhancement)
"""

import logging
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from dataclasses import dataclass, field
from datetime import datetime

from ..config.settings import Config

logger = logging.getLogger(__name__)

# Try to import LangGraph, fall back to simple implementation if not available
try:
    from langgraph.graph import StateGraph, END
    from typing_extensions import TypedDict
    LANGGRAPH_AVAILABLE = True
except ImportError:
    logger.warning("LangGraph not available, using fallback implementation")
    LANGGRAPH_AVAILABLE = False
    TypedDict = dict  # Fallback


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""
    success: bool
    items_processed: int
    items_new: int
    errors: List[str]
    metadata: Dict[str, Any]


class AgentState(TypedDict):
    """State for the LangGraph workflow."""
    config: Config
    phase: str
    raw_data: List[Dict[str, Any]]
    parsed_data: List[Dict[str, Any]]
    new_items: List[Dict[str, Any]]
    errors: List[str]
    processed_count: int
    new_count: int
    should_notify: bool
    timestamp: str


def _create_initial_state(config: Config) -> AgentState:
    """Create initial workflow state."""
    return {
        "config": config,
        "phase": "init",
        "raw_data": [],
        "parsed_data": [],
        "new_items": [],
        "errors": [],
        "processed_count": 0,
        "new_count": 0,
        "should_notify": False,
        "timestamp": datetime.now().isoformat(),
    }


def crawl_node(state: AgentState) -> AgentState:
    """Crawl node: Fetch raw data from target."""
    logger.info("Starting crawl phase")

    try:
        from ..crawlers import get_crawler

        config = state["config"]
        crawler = get_crawler(config)
        results = crawler.crawl()

        state["raw_data"] = results
        state["phase"] = "crawl"
        logger.info(f"Crawled {len(results)} items")

    except Exception as e:
        logger.error(f"Crawl phase failed: {e}")
        state["errors"].append(f"Crawl error: {str(e)}")

    return state


def parse_node(state: AgentState) -> AgentState:
    """Parse node: Process raw data into structured format."""
    logger.info("Starting parse phase")

    try:
        from ..parsers import get_parser

        config = state["config"]
        parser = get_parser(config)
        parsed = []

        for item in state["raw_data"]:
            try:
                parsed_item = parser.parse(item)
                if parsed_item:
                    parsed.append(parsed_item)
            except Exception as e:
                logger.error(f"Failed to parse item: {e}")
                state["errors"].append(f"Parse error: {str(e)}")

        state["parsed_data"] = parsed
        state["phase"] = "parse"
        logger.info(f"Parsed {len(parsed)} items")

    except Exception as e:
        logger.error(f"Parse phase failed: {e}")
        state["errors"].append(f"Parse phase error: {str(e)}")

    return state


def storage_node(state: AgentState) -> AgentState:
    """Storage node: Store items and filter new ones."""
    logger.info("Starting storage phase")

    try:
        from ..storage import get_storage

        config = state["config"]
        storage = get_storage(config)

        # Use batch operations for better performance
        new_items = storage.batch_check_and_store(state["parsed_data"])

        state["new_items"] = new_items
        state["new_count"] = len(new_items)
        state["processed_count"] = len(state["parsed_data"])
        state["should_notify"] = len(new_items) > 0
        state["phase"] = "storage"
        logger.info(f"Batch stored {len(new_items)} new items out of {len(state['parsed_data'])} processed")

    except Exception as e:
        logger.error(f"Storage phase failed: {e}")
        state["errors"].append(f"Storage phase error: {str(e)}")

    return state


def notify_node(state: AgentState) -> AgentState:
    """Notify node: Send notifications for new items."""
    if not state["new_items"]:
        logger.info("No new items to notify")
        state["phase"] = "complete"
        return state

    logger.info(f"Starting notification phase for {len(state['new_items'])} items")

    try:
        from ..notify import get_notifier

        config = state["config"]
        notifier = get_notifier(config)
        notifier.send(state["new_items"])

        state["phase"] = "notify"
        logger.info("Notifications sent successfully")

    except Exception as e:
        logger.error(f"Notification failed: {e}")
        state["errors"].append(f"Notification error: {str(e)}")

    return state


def should_continue(state: AgentState) -> str:
    """Decide whether to continue workflow or handle errors."""
    # If we have critical errors, stop
    if len(state["errors"]) > 10:  # Threshold for too many errors
        logger.warning("Too many errors, stopping workflow")
        return "end"

    # If no raw data, stop
    if state["phase"] == "crawl" and not state["raw_data"]:
        logger.warning("No data crawled, stopping workflow")
        return "end"

    # Continue normal flow
    return "continue"


def check_should_notify(state: AgentState) -> str:
    """Decide whether to send notifications."""
    return "notify" if state["should_notify"] else "end"


class CoordinatorAgent:
    """Main coordinator agent for MoAgent workflow using LangGraph."""

    def __init__(self, config: Config, use_langgraph: bool = True):
        """
        Initialize coordinator agent.

        Args:
            config: Configuration object
            use_langgraph: Force use of LangGraph (default: True, auto-falls back if unavailable)
        """
        self.config = config
        self.use_langgraph = use_langgraph and LANGGRAPH_AVAILABLE

        if self.use_langgraph:
            self.workflow = self._build_langgraph_workflow()
            logger.info(f"CoordinatorAgent initialized with LangGraph, mode: {config.crawl_mode}")
        else:
            logger.info(f"CoordinatorAgent initialized (fallback mode), mode: {config.crawl_mode}")

    def _build_langgraph_workflow(self) -> Optional['StateGraph']:
        """Build LangGraph StateGraph workflow."""
        if not LANGGRAPH_AVAILABLE:
            return None

        # Create state graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("crawl", crawl_node)
        workflow.add_node("parse", parse_node)
        workflow.add_node("storage", storage_node)
        workflow.add_node("notify", notify_node)

        # Set entry point
        workflow.set_entry_point("crawl")

        # Add edges
        workflow.add_edge("crawl", "parse")
        workflow.add_edge("parse", "storage")

        # Conditional edge: should we notify?
        workflow.add_conditional_edges(
            "storage",
            check_should_notify,
            {
                "notify": "notify",
                "end": END,
            }
        )

        workflow.add_edge("notify", END)

        # Compile the graph
        return workflow.compile()

    def run(self) -> WorkflowResult:
        """
        Execute the main agent workflow.

        Returns:
            WorkflowResult with execution summary
        """
        logger.info("Starting coordinator workflow")

        try:
            if self.use_langgraph and self.workflow:
                return self._run_langgraph()
            else:
                return self._run_fallback()

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return WorkflowResult(
                success=False,
                items_processed=0,
                items_new=0,
                errors=[str(e)],
                metadata={}
            )

    def _run_langgraph(self) -> WorkflowResult:
        """Run workflow using LangGraph."""
        logger.info("Running LangGraph workflow")

        # Initialize state
        initial_state = _create_initial_state(self.config)

        # Invoke the graph
        final_state = self.workflow.invoke(initial_state)

        # Build result
        return WorkflowResult(
            success=len(final_state["errors"]) == 0,
            items_processed=final_state["processed_count"],
            items_new=final_state["new_count"],
            errors=final_state["errors"],
            metadata={
                "target_url": self.config.target_url,
                "crawl_mode": self.config.crawl_mode,
                "timestamp": final_state["timestamp"],
                "engine": "langgraph",
            }
        )

    def _run_fallback(self) -> WorkflowResult:
        """Run workflow using simple sequential execution (fallback)."""
        logger.info("Running fallback workflow")

        # Initialize state
        state = _create_initial_state(self.config)

        # Execute nodes sequentially
        state = crawl_node(state)
        state = parse_node(state)
        state = storage_node(state)

        if state["should_notify"]:
            state = notify_node(state)

        # Build result
        return WorkflowResult(
            success=len(state["errors"]) == 0,
            items_processed=state["processed_count"],
            items_new=state["new_count"],
            errors=state["errors"],
            metadata={
                "target_url": self.config.target_url,
                "crawl_mode": self.config.crawl_mode,
                "timestamp": state["timestamp"],
                "engine": "fallback",
            }
        )
