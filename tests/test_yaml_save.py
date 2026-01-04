import yaml

from moagent.agents.pattern_generator.llm_pattern_generator import (
    LLMPatternGeneratorAgent,
)
from moagent.llm.client import get_llm_client

# Create a pattern generator
generator = LLMPatternGeneratorAgent()

# Create a mock analysis
from moagent.agents.pattern_generator.llm_pattern_generator import LLMPatternAnalysis

analysis = LLMPatternAnalysis(
    list_container={'tag': 'div', 'class': 'news-list'},
    item_selector={'tag': 'div', 'class': 'item'},
    title_selector={'tag': 'h2', 'class': 'title'},
    url_selector={'tag': 'a', 'attr': 'href'},
    date_selector=None,
    content_selector=None,
    post_process={},
    confidence=0.85,
    reasoning='Mock analysis for testing',
    sample_html='<html></html>',
    llm_response={}
)

# Try to generate YAML config
config = generator.generate_config_yaml(analysis, 'test_pattern', 'https://example.com')

# Try to serialize to YAML
try:
    yaml_str = yaml.safe_dump(config, default_flow_style=False, allow_unicode=True)
    print('✅ YAML serialization successful!')
    print('Generated config keys:', list(config.keys()))
    print('LLM metadata keys:', list(config['crawler_patterns']['_llm_metadata'].keys()))
except Exception as e:
    print(f'❌ YAML serialization failed: {e}')
