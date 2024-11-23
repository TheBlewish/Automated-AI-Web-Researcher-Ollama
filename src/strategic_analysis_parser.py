from typing import List, Dict, Optional, Union
import re
import logging
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ResearchFocus:
    """Represents a specific area of research focus"""
    area: str
    priority: int
    source_query: str = ""
    timestamp: str = ""
    search_queries: List[str] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.search_queries is None:
            self.search_queries = []

@dataclass
class AnalysisResult:
    """Contains the complete analysis result"""
    original_question: str
    focus_areas: List[ResearchFocus]
    raw_response: str
    timestamp: str = ""
    confidence_score: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Set up logging
logger = logging.getLogger(__name__)

class StrategicAnalysisParser:
    """Enhanced parser with improved pattern matching and validation"""
    def __init__(self):
        self.patterns = {
            'original_question': [
                r"(?i)original question analysis:\s*(.*?)(?=research gap|$)",
                r"(?i)original query:\s*(.*?)(?=research gap|$)",
                r"(?i)research question:\s*(.*?)(?=research gap|$)",
                r"(?i)topic analysis:\s*(.*?)(?=research gap|$)"
            ],
            'research_gaps': [
                r"(?i)research gaps?:\s*",
                r"(?i)gaps identified:\s*",
                r"(?i)areas for research:\s*",
                r"(?i)investigation areas:\s*"
            ],
            'priority': [
                r"(?i)priority:\s*(\d+)",
                r"(?i)priority level:\s*(\d+)",
                r"(?i)\(priority:\s*(\d+)\)",
                r"(?i)importance:\s*(\d+)"
            ]
        }
        self.logger = logging.getLogger(__name__)

    def parse_analysis(self, llm_response: str) -> Optional[AnalysisResult]:
        """Main parsing method with improved validation"""
        try:
            # Clean and normalize the response
            cleaned_response = self._clean_text(llm_response)

            # Extract original question with validation
            original_question = self._extract_original_question(cleaned_response)
            if not original_question:
                self.logger.warning("Failed to extract original question")
                original_question = "Original question extraction failed"

            # Extract and validate research areas
            focus_areas = self._extract_research_areas(cleaned_response)
            focus_areas = self._normalize_focus_areas(focus_areas)

            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(original_question, focus_areas)

            return AnalysisResult(
                original_question=original_question,
                focus_areas=focus_areas,
                raw_response=llm_response,
                confidence_score=confidence_score
            )

        except Exception as e:
            self.logger.error(f"Error in parse_analysis: {str(e)}")
            return None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for parsing"""
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'\s{2,}', ' ', text)
        text = re.sub(r'(\d+\))', r'\1.', text)
        return text.strip()

    def _extract_original_question(self, text: str) -> str:
        """Extract original question with improved matching"""
        for pattern in self.patterns['original_question']:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return self._clean_text(match.group(1))
        return ""

    def _extract_research_areas(self, text: str) -> List[ResearchFocus]:
        """Extract research areas with enhanced validation"""
        areas = []
        for pattern in self.patterns['research_gaps']:
            gap_match = re.search(pattern, text)
            if gap_match:
                sections = re.split(r'\n\s*\d+[\.)]\s+', text[gap_match.end():])
                sections = [s for s in sections if s.strip()]

                for section in sections:
                    focus = self._parse_research_focus(section)
                    if focus and self._is_valid_focus(focus):
                        areas.append(focus)
                break
        return areas

    def _parse_research_focus(self, text: str) -> Optional[ResearchFocus]:
        """Parse research focus with improved validation without reasoning."""
        try:
            # Extract area
            area = text.split('\n')[0].strip()

            # Extract and validate priority
            priority = self._extract_priority(text)

            # Return ResearchFocus without reasoning
            return ResearchFocus(
                area=area,
                priority=priority
            )

        except Exception as e:
            self.logger.error(f"Error parsing research focus: {str(e)}")
            return None

    def _extract_priority(self, text: str) -> int:
        """Extract priority with validation"""
        for pattern in self.patterns['priority']:
            priority_match = re.search(pattern, text)
            if priority_match:
                try:
                    priority = int(priority_match.group(1))
                    return max(1, min(5, priority))
                except ValueError:
                    continue
        return 3  # Default priority

    def _is_valid_focus(self, focus: ResearchFocus) -> bool:
        """Validate research focus completeness and quality"""
        if not focus.area:  # Only check if area exists and isn't empty
            return False
        if focus.priority < 1 or focus.priority > 5:
            return False
        return True

    def _normalize_focus_areas(self, areas: List[ResearchFocus]) -> List[ResearchFocus]:
        """Normalize and validate focus areas"""
        normalized = []
        for area in areas:
            if not area.area.strip():
                continue

            area.priority = max(1, min(5, area.priority))

            if self._is_valid_focus(area):
                normalized.append(area)

        # Sort by priority (highest first) but don't add any filler areas
        normalized.sort(key=lambda x: x.priority, reverse=True)

        return normalized

    def _calculate_confidence_score(self, question: str, areas: List[ResearchFocus]) -> float:
        """Calculate confidence score for analysis quality"""
        score = 0.0

        # Question quality (0.3)
        if question and len(question.split()) >= 3:
            score += 0.3

        # Areas quality (0.7)
        if areas:
            # Valid areas ratio (0.35) - now based on proportion that are valid vs total
            num_areas = len(areas)
            if num_areas > 0:  # Avoid division by zero
                valid_areas = sum(1 for a in areas if self._is_valid_focus(a))
                score += 0.35 * (valid_areas / num_areas)

            # Priority distribution (0.35) - now based on having different priorities
            if num_areas > 0:  # Avoid division by zero
                unique_priorities = len(set(a.priority for a in areas))
                score += 0.35 * (unique_priorities / num_areas)

        return round(score, 2)

    def format_analysis_result(self, result: AnalysisResult) -> str:
        """Format analysis result for display without reasoning."""
        formatted = [
            "Strategic Analysis Result",
            "=" * 80,
            f"\nOriginal Question Analysis:\n{result.original_question}\n",
            f"Analysis Confidence Score: {result.confidence_score}",
            "\nResearch Focus Areas:"
        ]

        for i, focus in enumerate(result.focus_areas, 1):
            formatted.extend([
                f"\n{i}. {focus.area}",
                f"   Priority: {focus.priority}"
            ])

        return "\n".join(formatted)
