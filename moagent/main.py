"""
Main execution logic for MoAgent.
"""

import logging
from typing import Optional

from .config.settings import Config
from .agents.coordinator import CoordinatorAgent

logger = logging.getLogger(__name__)


def run_agent(config: Config) -> None:
    """
    Main entry point for running the MoAgent system.

    Args:
        config: Configuration object with all settings
    """
    logger.info("Initializing MoAgent system")

    # Initialize coordinator agent
    coordinator = CoordinatorAgent(config)

    # Run the agent workflow
    try:
        logger.info("Starting agent workflow")
        result = coordinator.run()

        logger.info(f"Workflow completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Agent workflow failed: {e}")
        raise


def main():
    """Main entry point for CLI usage."""
    from .cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
