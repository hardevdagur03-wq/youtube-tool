"""Grammar Optimizer — fixes grammar, punctuation, spelling, and sentence structure."""

from __future__ import annotations
import logging
import re
from typing import Any

from optimization.optimization_models import OptimizationContext, OptimizationType
from optimization.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


COMMON_MISSPELLINGS = {
    "recieve": "receive", "acheive": "achieve", "seperate": "separate",
    "definately": "definitely", "occured": "occurred", "occuring": "occurring",
    "occurance": "occurrence", "prefered": "preferred", "refered": "referred",
    "transfered": "transferred", "adress": "address", "alot": "a lot",
    "buisness": "business", "calender": "calendar", "catagory": "category",
    "commited": "committed", "commitee": "committee", "concious": "conscious",
    "enviroment": "environment", "exagerate": "exaggerate", "excellant": "excellent",
    "foriegn": "foreign", "fourty": "forty", "freind": "friend",
    "goverment": "government", "grammer": "grammar", "harrass": "harass",
    "hierachy": "hierarchy", "independant": "independent", "knowlege": "knowledge",
    "libary": "library", "maintainance": "maintenance", "millenium": "millennium",
    "mispell": "misspell", "neccessary": "necessary", "nieghbor": "neighbor",
    "occassion": "occasion", "oppertunity": "opportunity", "originaly": "originally",
    "paralell": "parallel", "posession": "possession", "preceeding": "preceding",
    "privilege": "privilege", "protaganist": "protagonist",
    "publically": "publicly", "reciept": "receipt", "reccomend": "recommend",
    "referance": "reference", "remeber": "remember", "repetition": "repetition",
    "restaraunt": "restaurant", "rythm": "rhythm", "similer": "similar",
    "speach": "speech", "succesful": "successful", "succesfully": "successfully",
    "therfore": "therefore", "threshhold": "threshold", "tommorow": "tomorrow",
    "truely": "truly", "untill": "until", "usally": "usually",
    "vaccume": "vacuum", "vegitables": "vegetables", "wierd": "weird",
    "writen": "written", "yatch": "yacht",
}


class GrammarOptimizer:
    """Corrects grammar, punctuation, spelling, and sentence structure."""

    def __init__(self, prompt_builder: PromptBuilder | None = None):
        self._prompt_builder = prompt_builder or PromptBuilder()

    def optimize(
        self,
        context: OptimizationContext,
        llm_call: callable,
    ) -> tuple[str, list[str]]:
        prompt = self._prompt_builder.build_prompt(context, OptimizationType.GRAMMAR)
        warnings: list[str] = []
        optimized = ""

        # First pass: quick rule-based fixes
        quick_fixed, quick_warnings = self._quick_grammar_fixes(context.section_text)
        corrected_context = context.model_copy(update={"section_text": quick_fixed})
        prompt = self._prompt_builder.build_prompt(corrected_context, OptimizationType.GRAMMAR)
        warnings.extend(quick_warnings)

        try:
            optimized = llm_call(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
                temperature=0.2,
                max_tokens=2048,
            )
            optimized = optimized.strip()
        except Exception as exc:
            logger.error("[GrammarOptimizer] LLM call failed: %s", exc)
            warnings.append(f"Grammar optimization LLM call failed: {exc}")
            return quick_fixed, warnings

        if not optimized:
            warnings.append("Grammar optimization returned empty, using quick fixes")
            return quick_fixed, warnings

        if len(optimized) < len(context.section_text) * 0.5:
            warnings.append("Optimized content too short, using quick fixes")
            return quick_fixed, warnings

        return optimized, warnings

    def _quick_grammar_fixes(self, text: str) -> tuple[str, list[str]]:
        modified = text
        fixes: list[str] = []

        # Fix common misspellings
        for wrong, correct in COMMON_MISSPELLINGS.items():
            pattern = re.compile(r'\b' + re.escape(wrong) + r'\b', re.IGNORECASE)
            if pattern.search(modified):
                modified = pattern.sub(correct, modified)
                fixes.append(f"Fixed spelling: '{wrong}' -> '{correct}'")

        # Fix capitalization at start of sentences
        sentences = re.split(r'(?<=[.!?])\s+', modified)
        fixed_sentences = []
        for sent in sentences:
            stripped = sent.strip()
            if stripped and stripped[0].islower():
                stripped = stripped[0].upper() + stripped[1:]
                fixes.append(f"Capitalized sentence start: '{stripped[:30]}...'")
            fixed_sentences.append(stripped)
        modified = " ".join(fixed_sentences)

        return modified, fixes
