import os, re
from typing import List, Dict, Any, Optional, Tuple
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, PatternRecognizer, Pattern, RecognizerResult
from presidio_analyzer.nlp_engine import SpacyNlpEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

_analyzer: Optional[AnalyzerEngine] = None
_anonymizer: Optional[AnonymizerEngine] = None

def _build_recognizers(registry: RecognizerRegistry):
    # India Aadhaar (12 digits, with optional spaces)
    aadhaar = PatternRecognizer(
        supported_entity="IN_AADHAAR",
        name="aadhaar_pattern",
        patterns=[Pattern("aadhaar", r"\b\d{4}\s?\d{4}\s?\d{4}\b", 0.5)],
    )
    # India PAN (5 letters + 4 digits + 1 letter)
    pan = PatternRecognizer(
        supported_entity="IN_PAN",
        name="pan_pattern",
        patterns=[Pattern("pan", r"\b[A-Z]{5}\d{4}[A-Z]\b", 0.6)],
    )
    # India Passport (simple common form: letter + 7 digits, excluding some letters)
    in_passport = PatternRecognizer(
        supported_entity="IN_PASSPORT",
        name="in_passport_pattern",
        patterns=[Pattern("in_passport", r"\b[A-PR-WY][1-9]\d{6}\b", 0.5)],
    )
    registry.add_recognizer(aadhaar)
    registry.add_recognizer(pan)
    registry.add_recognizer(in_passport)

def _get_analyzer() -> Tuple[AnalyzerEngine, AnonymizerEngine]:
    global _analyzer, _anonymizer
    if _analyzer and _anonymizer:
        return _analyzer, _anonymizer

    lang = os.getenv("PRESIDIO_LANGUAGE", "en")
    spacy_model = os.getenv("SPACY_MODEL", "en_core_web_lg")

    nlp_engine = SpacyNlpEngine(models=[{"lang_code": lang, "model_name": spacy_model}])
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers()
    _build_recognizers(registry)

    _analyzer = AnalyzerEngine(nlp_engine=nlp_engine, registry=registry)
    _anonymizer = AnonymizerEngine()
    return _analyzer, _anonymizer

def analyze_presidio(
    text: str,
    language: str,
    entities: Optional[List[str]],
    global_threshold: float,
    per_entity_threshold: Dict[str, float],
) -> List[RecognizerResult]:
    analyzer, _ = _get_analyzer()
    results = analyzer.analyze(
        text=text,
        language=language,
        entities=entities,
        score_threshold=min(0.01, global_threshold),  # run loose, filter below
    )
    out: List[RecognizerResult] = []
    for r in results:
        th = per_entity_threshold.get(r.entity_type, global_threshold)
        if (r.score or 0) >= th:
            out.append(r)
    return out

def anonymize_presidio(text: str, results: List[RecognizerResult], placeholders: Dict[str, str]) -> str:
    _, anonymizer = _get_analyzer()
    ops = {}
    default_token = placeholders.get("DEFAULT", "[REDACTED]")

    def tok(ent, default):
        return placeholders.get(ent, placeholders.get(ent.upper(), default))

    for r in results:
        ent = r.entity_type
        ops[ent] = OperatorConfig("replace", {"new_value": tok(ent, default_token)})
    ops["DEFAULT"] = OperatorConfig("replace", {"new_value": default_token})

    result = anonymizer.anonymize(text=text, analyzer_results=results, anonymizers_config=ops)
    return result.text
