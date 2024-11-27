import re
from typing import Dict, List, Union, Optional
import logging
import json
from .strategic_analysis_parser import StrategicAnalysisParser, AnalysisResult, ResearchFocus

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UltimateLLMResponseParser:
    def __init__(self):
        self.decision_keywords = {
            'refine': ['refine', 'need more info', 'insufficient', 'unclear', 'more research', 'additional search'],
            'answer': ['answer', 'sufficient', 'enough info', 'can respond', 'adequate', 'comprehensive']
        }
        self.section_identifiers = [
            ('decision', r'(?i)decision\s*:'),
            ('reasoning', r'(?i)reasoning\s*:'),
            ('selected_results', r'(?i)selected results\s*:'),
            ('response', r'(?i)response\s*:')
        ]
        # Initialize strategic analysis parser
        self.strategic_parser = StrategicAnalysisParser()

    def parse_llm_response(self, response: str, mode: str = 'search') -> Dict[str, Union[str, List[int], AnalysisResult]]:
        """
        Parse LLM response based on mode

        Args:
            response (str): The LLM's response text
            mode (str): 'search' for web search, 'research' for strategic analysis

        Returns:
            Dict containing parsed response
        """
        logger.info(f"Starting to parse LLM response in {mode} mode")

        if mode == 'research':
            return self._parse_research_response(response)

        # Original search mode parsing
        result = {
            'decision': None,
            'reasoning': None,
            'selected_results': [],
            'response': None
        }

        parsing_strategies = [
            self._parse_structured_response,
            self._parse_json_response,
            self._parse_unstructured_response,
            self._parse_implicit_response
        ]

        for strategy in parsing_strategies:
            try:
                parsed_result = strategy(response)
                if self._is_valid_result(parsed_result):
                    result.update(parsed_result)
                    logger.info(f"Successfully parsed using strategy: {strategy.__name__}")
                    break
            except Exception as e:
                logger.warning(f"Error in parsing strategy {strategy.__name__}: {str(e)}")

        if not self._is_valid_result(result):
            logger.warning("All parsing strategies failed. Using fallback parsing.")
            result = self._fallback_parsing(response)

        result = self._post_process_result(result)

        logger.info("Finished parsing LLM response")
        return result

    def _parse_research_response(self, response: str) -> Dict[str, Union[str, AnalysisResult]]:
        """Handle research mode specific parsing"""
        try:
            analysis_result = self.strategic_parser.parse_analysis(response)
            if analysis_result:
                return {
                    'mode': 'research',
                    'analysis_result': analysis_result,
                    'error': None
                }
            else:
                logger.error("Failed to parse strategic analysis")
                return {
                    'mode': 'research',
                    'analysis_result': None,
                    'error': 'Failed to parse strategic analysis'
                }
        except Exception as e:
            logger.error(f"Error in research response parsing: {str(e)}")
            return {
                'mode': 'research',
                'analysis_result': None,
                'error': str(e)
            }

    def parse_search_query(self, query_response: str) -> Dict[str, str]:
        """Parse search query formulation response"""
        try:
            lines = query_response.strip().split('\n')
            result = {
                'query': '',
                'time_range': 'none'
            }

            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()

                    if 'query' in key:
                        result['query'] = self._clean_query(value)
                    elif 'time' in key or 'range' in key:
                        result['time_range'] = self._validate_time_range(value)

            return result
        except Exception as e:
            logger.error(f"Error parsing search query: {str(e)}")
            return {'query': '', 'time_range': 'none'}

    def _parse_structured_response(self, response: str) -> Dict[str, Union[str, List[int]]]:
        result = {}
        for key, pattern in self.section_identifiers:
            match = re.search(f'{pattern}(.*?)(?={"|".join([p for k, p in self.section_identifiers if k != key])}|$)',
                            response, re.IGNORECASE | re.DOTALL)
            if match:
                result[key] = match.group(1).strip()

        if 'selected_results' in result:
            result['selected_results'] = self._extract_numbers(result['selected_results'])

        return result

    def _parse_json_response(self, response: str) -> Dict[str, Union[str, List[int]]]:
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed_json = json.loads(json_str)
                return {k: v for k, v in parsed_json.items()
                       if k in ['decision', 'reasoning', 'selected_results', 'response']}
        except json.JSONDecodeError:
            pass
        return {}

    def _parse_unstructured_response(self, response: str) -> Dict[str, Union[str, List[int]]]:
        result = {}
        lines = response.split('\n')
        current_section = None

        for line in lines:
            section_match = re.match(r'(.+?)[:.-](.+)', line)
            if section_match:
                key = self._match_section_to_key(section_match.group(1))
                if key:
                    current_section = key
                    result[key] = section_match.group(2).strip()
            elif current_section:
                result[current_section] += ' ' + line.strip()

        if 'selected_results' in result:
            result['selected_results'] = self._extract_numbers(result['selected_results'])

        return result

    def _parse_implicit_response(self, response: str) -> Dict[str, Union[str, List[int]]]:
        result = {}

        decision = self._infer_decision(response)
        if decision:
            result['decision'] = decision

        numbers = self._extract_numbers(response)
        if numbers:
            result['selected_results'] = numbers

        if not result:
            result['response'] = response.strip()

        return result

    def _fallback_parsing(self, response: str) -> Dict[str, Union[str, List[int]]]:
        return {
            'decision': self._infer_decision(response),
            'reasoning': None,
            'selected_results': self._extract_numbers(response),
            'response': response.strip()
        }

    def _post_process_result(self, result: Dict[str, Union[str, List[int]]]) -> Dict[str, Union[str, List[int]]]:
        if result['decision'] not in ['refine', 'answer']:
            result['decision'] = self._infer_decision(str(result))

        if not isinstance(result['selected_results'], list):
            result['selected_results'] = self._extract_numbers(str(result['selected_results']))

        result['selected_results'] = result['selected_results'][:2]

        if not result['reasoning']:
            result['reasoning'] = f"Based on the {'presence' if result['selected_results'] else 'absence'} of selected results and the overall content."

        if not result['response']:
            result['response'] = result.get('reasoning', 'No clear response found.')

        return result

    def _match_section_to_key(self, section: str) -> Optional[str]:
        for key, pattern in self.section_identifiers:
            if re.search(pattern, section, re.IGNORECASE):
                return key
        return None

    def _extract_numbers(self, text: str) -> List[int]:
        return [int(num) for num in re.findall(r'\b(?:10|[1-9])\b', text)]

    def _infer_decision(self, text: str) -> str:
        text = text.lower()
        refine_score = sum(text.count(keyword) for keyword in self.decision_keywords['refine'])
        answer_score = sum(text.count(keyword) for keyword in self.decision_keywords['answer'])
        return 'refine' if refine_score > answer_score else 'answer'

    def _is_valid_result(self, result: Dict[str, Union[str, List[int]]]) -> bool:
        return bool(result.get('decision') or result.get('response') or result.get('selected_results'))

    def _clean_query(self, query: str) -> str:
        """Clean and validate search query"""
        query = re.sub(r'["\'\[\]]', '', query)
        query = re.sub(r'\s+', ' ', query)
        return query.strip()[:100]

    def _validate_time_range(self, time_range: str) -> str:
        """Validate time range value"""
        valid_ranges = ['d', 'w', 'm', 'y', 'none']
        time_range = time_range.lower()
        return time_range if time_range in valid_ranges else 'none'
