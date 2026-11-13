import hashlib
from app.services.analyzers.base_analyzer import SimilarityAnalyzer, AnalysisResult, MatchSource

class DemoSimilarityAnalyzer(SimilarityAnalyzer):
    """
    Polymorphic Concrete Implementation of SimilarityAnalyzer.
    Generates deterministic, clearly labelled synthetic analysis for development and testing.
    Does NOT pretend to be an actual external plagiarism engine.
    """

    def analyze(self, submission_id: int, submission_code: str, file_reference: str | None = None) -> AnalysisResult:
        # Deterministic simulation based on hash of submission code
        code_hash = int(hashlib.md5(submission_code.encode("utf-8")).hexdigest()[:6], 16)

        # Generate realistic distribution: mostly low/moderate, occasional high
        normalized = (code_hash % 1000) / 10.0  # 0.0 to 99.9

        # Decompose into legitimate quotations, common template, and external match
        quotation_pct = round(min(normalized * 0.25, 20.0), 2)
        template_pct = round(min(normalized * 0.20, 15.0), 2)
        internet_pct = round(max(0.0, normalized - quotation_pct - template_pct), 2)
        overall_score = round(normalized, 2)

        matches = []
        if quotation_pct > 0:
            matches.append(MatchSource(
                source_type="QUOTATION",
                source_reference="IEEE Standard Glossary & Documented Sources",
                matched_percentage=quotation_pct,
                description="Properly enclosed and cited references."
            ))
        if template_pct > 0:
            matches.append(MatchSource(
                source_type="TEMPLATE",
                source_reference="Course Starter Boilerplate / Assignment Skeleton",
                matched_percentage=template_pct,
                description="Common starter code provided by course instructor."
            ))
        if internet_pct > 0:
            matches.append(MatchSource(
                source_type="INTERNET",
                source_reference="Public Academic Repository & Online Resources",
                matched_percentage=internet_pct,
                description="Text overlap detected in indexed external repositories."
            ))

        return AnalysisResult(
            overall_score=overall_score,
            quotation_percentage=quotation_pct,
            template_percentage=template_pct,
            internet_percentage=internet_pct,
            matches=matches,
            engine_name="DemoSimilarityAnalyzer (Simulated Engine)",
            is_simulated=True
        )

