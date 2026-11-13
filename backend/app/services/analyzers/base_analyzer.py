from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class MatchSource:
    source_type: str  # QUOTATION, TEMPLATE, INTERNET, PEER_SUBMISSION
    source_reference: str
    matched_percentage: float
    description: str

@dataclass
class AnalysisResult:
    overall_score: float
    quotation_percentage: float
    template_percentage: float
    internet_percentage: float
    matches: List[MatchSource] = field(default_factory=list)
    engine_name: str = "AbstractEngine"
    is_simulated: bool = False

class SimilarityAnalyzer(ABC):
    """
    Abstract Base Class (Abstraction) for Similarity Analysis Engines.
    Polymorphic subclasses implement the specific analysis strategy
    (e.g. simulated demo, internal AST diffing, or external SaaS integration).
    """

    @abstractmethod
    def analyze(self, submission_id: int, submission_code: str, file_reference: str | None = None) -> AnalysisResult:
        """
        Executes similarity analysis and returns an AnalysisResult contract.
        Must be implemented by concrete subclasses.
        """
        pass

