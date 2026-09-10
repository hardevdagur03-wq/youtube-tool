"""Grammar Validation — Phase 9.

Checks spelling, grammar, punctuation, passive voice, sentence structure.
Uses heuristics and pattern matching for deterministic analysis.
"""

from __future__ import annotations
import re
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest, GrammarResult, ReviewIssue, IssueSeverity


class GrammarValidator(BaseValidator):
    """Validates grammar, spelling, punctuation, and sentence structure."""

    PASSIVE_PATTERNS = [
        r'\b(is|are|was|were|be|been|being)\s+\w+ed\b',
        r'\b(is|are|was|were|be|been|being)\s+\w+en\b',
        r'\b(has|have|had)\s+been\s+\w+ed\b',
        r'\b(is|are|was|were)\s+being\s+\w+ed\b',
    ]

    RUN_ON_INDICATORS = [
        r'[,;]\s+(however|therefore|nevertheless|furthermore|meanwhile)\s*[,;]',
    ]

    FRAGMENT_INDICATORS = [
        r'^(Because|Since|Although|Unless|While|If|When)\s+\w+[^.?!]*$',
    ]

    REPEATED_WORDS = [
        r'\b(\w+)\s+\1\b',
    ]

    COMMON_MISSPELLINGS = {
        "recieve": "receive",
        "acheive": "achieve",
        "seperate": "separate",
        "definately": "definitely",
        "occured": "occurred",
        "occuring": "occurring",
        "occurance": "occurrence",
        "prefered": "preferred",
        "refered": "referred",
        "transfered": "transferred",
        "adress": "address",
        "alot": "a lot",
        "allright": "all right",
        "alright": "all right",
        "buisness": "business",
        "calender": "calendar",
        "camouflage": "camouflage",
        "catagory": "category",
        "changable": "changeable",
        "choosen": "chosen",
        "committe": "committee",
        "commited": "committed",
        "commitee": "committee",
        "concious": "conscious",
        "congradulate": "congratulate",
        "connoisseur": "connoisseur",
        "conversation": "conservation",
        "daigram": "diagram",
        "decaffinated": "decaffeinated",
        "definance": "defiance",
        "desparate": "desperate",
        "dilema": "dilemma",
        "disapear": "disappear",
        "disapoint": "disappoint",
        "disasterous": "disastrous",
        "embarass": "embarrass",
        "enviroment": "environment",
        "exagerate": "exaggerate",
        "excellant": "excellent",
        "extraterestial": "extraterrestrial",
        "facist": "fascist",
        "famoust": "famous",
        "finaly": "finally",
        "florescent": "fluorescent",
        "foriegn": "foreign",
        "fourty": "forty",
        "foward": "forward",
        "freind": "friend",
        "fundemental": "fundamental",
        "gaurd": "guard",
        "glamourous": "glamorous",
        "goverment": "government",
        "grammer": "grammar",
        "grovelling": "groveling",
        "harrass": "harass",
        "harrasment": "harassment",
        "hemorage": "hemorrhage",
        "hierachical": "hierarchical",
        "hierachy": "hierarchy",
        "humoural": "humoral",
        "hypocracy": "hypocrisy",
        "idiosyncracy": "idiosyncrasy",
        "illicit": "elicit",
        "imaginery": "imaginary",
        "immitate": "imitate",
        "immidiate": "immediate",
        "incidently": "incidentally",
        "independant": "independent",
        "interbread": "interbreed",
        "interum": "interim",
        "irrevelant": "irrelevant",
        "jepardy": "jeopardy",
        "knowlege": "knowledge",
        "legitamate": "legitimate",
        "libary": "library",
        "lieing": "lying",
        "maintainance": "maintenance",
        "millenia": "millennia",
        "millenium": "millennium",
        "mischievious": "mischievous",
        "mispell": "misspell",
        "momento": "memento",
        "monestary": "monastery",
        "monkies": "monkeys",
        "neccessary": "necessary",
        "neutal": "neutral",
        "nieghbor": "neighbor",
        "ninteenth": "nineteenth",
        "noticable": "noticeable",
        "occassion": "occasion",
        "oppertunity": "opportunity",
        "oregon": "origin",
        "originaly": "originally",
        "overriden": "overridden",
        "pamplet": "pamphlet",
        "paralell": "parallel",
        "paralysis": "paralysis",
        "pasttime": "pastime",
        "plesant": "pleasant",
        "politican": "politician",
        "portayed": "portrayed",
        "posession": "possession",
        "practically": "practically",
        "preceeding": "preceding",
        "precurser": "precursor",
        "preferrably": "preferably",
        "preserverance": "perseverance",
        "presue": "pursue",
        "privilege": "privilege",
        "protaganist": "protagonist",
        "psycholigical": "psychological",
        "publically": "publicly",
        "reciept": "receipt",
        "reccomend": "recommend",
        "reccommend": "recommend",
        "referance": "reference",
        "reguardless": "regardless",
        "reherse": "rehearse",
        "religous": "religious",
        "remeber": "remember",
        "reminiscient": "reminiscent",
        "repitition": "repetition",
        "restaraunt": "restaurant",
        "rythm": "rhythm",
        "sargeant": "sergeant",
        "seige": "siege",
        "similer": "similar",
        "skilful": "skillful",
        "sophmore": "sophomore",
        "speach": "speech",
        "sponser": "sponsor",
        "steriod": "steroid",
        "stragedy": "strategy",
        "strenous": "strenuous",
        "strentgh": "strength",
        "stubborness": "stubbornness",
        "substract": "subtract",
        "succesful": "successful",
        "succesfully": "successfully",
        "sufferred": "suffered",
        "supercede": "supersede",
        "supposably": "supposedly",
        "surounded": "surrounded",
        "surveilance": "surveillance",
        "symetric": "symmetric",
        "theatre": "theater",
        "therfore": "therefore",
        "threshhold": "threshold",
        "tommorow": "tomorrow",
        "tounge": "tongue",
        "truely": "truly",
        "unforetunately": "unfortunately",
        "untill": "until",
        "usally": "usually",
        "vaccume": "vacuum",
        "vegeterian": "vegetarian",
        "vegitables": "vegetables",
        "vigourous": "vigorous",
        "villian": "villain",
        "warefare": "warfare",
        "warrrior": "warrior",
        "weild": "wield",
        "wierd": "weird",
        "writen": "written",
        "yatch": "yacht",
    }

    def name(self) -> str:
        return "Grammar Validation"

    def validate(self, request: BlogReviewRequest) -> GrammarResult:
        text = request.content
        if not text:
            return GrammarResult(score=100.0)

        issues: list[ReviewIssue] = []
        spelling_errors = 0
        grammar_errors = 0
        punctuation_errors = 0
        passive_sentences = 0
        run_on_count = 0
        fragment_count = 0

        sentences = self._split_sentences(text)
        total_sentences = len(sentences) if sentences else 1

        # Check spelling
        for word in re.findall(r'\b[a-zA-Z]+\b', text):
            lower = word.lower()
            if lower in self.COMMON_MISSPELLINGS:
                spelling_errors += 1
                issues.append(ReviewIssue(
                    description=f"Possible misspelling: '{word}' should be '{self.COMMON_MISSPELLINGS[lower]}'",
                    location=self._find_location(text, word),
                    severity=IssueSeverity.LOW,
                    why_it_matters="Spelling errors reduce credibility and reader trust.",
                    recommended_fix=f"Replace '{word}' with '{self.COMMON_MISSPELLINGS[lower]}'",
                ))

        # Check passive voice
        for pattern in self.PASSIVE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            passive_sentences += len(matches)

        if passive_sentences > total_sentences * 0.3:
            issues.append(ReviewIssue(
                description=f"Passive voice used in approximately {passive_sentences} of {total_sentences} sentences ({passive_sentences * 100 // total_sentences}%)",
                location="General content",
                severity=IssueSeverity.MEDIUM,
                why_it_matters="Excessive passive voice makes content feel indirect and less engaging.",
                recommended_fix="Rewrite passive constructions in active voice where possible. E.g., 'The code was written by the team' → 'The team wrote the code'.",
            ))

        # Check run-on sentences
        for i, sent in enumerate(sentences):
            if len(sent.split()) > 35:
                run_on_count += 1
                if run_on_count <= 3:
                    issues.append(ReviewIssue(
                        description=f"Run-on sentence detected ({len(sent.split())} words): '{sent[:80]}...'",
                        location=f"Sentence {i + 1}",
                        severity=IssueSeverity.MEDIUM,
                        why_it_matters="Long, run-on sentences reduce readability and can confuse readers.",
                        recommended_fix="Split into 2-3 shorter sentences. Aim for 15-20 words per sentence.",
                    ))

        # Check sentence fragments
        for i, sent in enumerate(sentences):
            cleaned = sent.strip().rstrip('.?!')
            words = cleaned.split()
            if 1 <= len(words) <= 3 and not any(c in sent for c in [':', ';', '—', '-']):
                if not any(sent.startswith(w) for w in ['However', 'Therefore', 'Thus', 'Also', 'Additionally', 'Moreover']):
                    fragment_count += 1
                    if fragment_count <= 2:
                        issues.append(ReviewIssue(
                            description=f"Possible sentence fragment: '{sent.strip()}'",
                            location=f"Sentence {i + 1}",
                            severity=IssueSeverity.LOW,
                            why_it_matters="Sentence fragments can make writing feel choppy or incomplete.",
                            recommended_fix="Either expand into a complete sentence or connect to the previous sentence.",
                        ))

        # Check consecutive duplicate words
        for pattern in self.REPEATED_WORDS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                punctuation_errors += 1
                issues.append(ReviewIssue(
                    description=f"Repeated word: '{match.group(1)}' appears consecutively",
                    location=self._find_location(text, match.group(0)),
                    severity=IssueSeverity.LOW,
                    why_it_matters="Repeated words distract readers and appear unprofessional.",
                    recommended_fix=f"Remove the duplicate '{match.group(1)}'.",
                ))

        # Capitalization checks
        for i, sent in enumerate(sentences):
            stripped = sent.strip()
            if stripped and stripped[0].islower():
                grammar_errors += 1
                issues.append(ReviewIssue(
                    description=f"Sentence does not start with a capital letter: '{stripped[:60]}...'",
                    location=f"Sentence {i + 1}",
                    severity=IssueSeverity.MEDIUM,
                    why_it_matters="Incorrect capitalization undermines professionalism.",
                    recommended_fix=f"Capitalize the first letter: '{stripped[0].upper()}{stripped[1:]}'",
                ))

        # Calculate score
        total_errors = spelling_errors + grammar_errors + punctuation_errors
        penalty = min(total_errors * 5, 50)
        passive_penalty = max(0, (passive_sentences / total_sentences - 0.3) * 20)
        score = max(0, 100 - penalty - passive_penalty)

        return GrammarResult(
            score=round(score, 1),
            issues=issues,
            spelling_errors=spelling_errors,
            grammar_errors=grammar_errors,
            punctuation_errors=punctuation_errors,
            passive_voice_sentences=passive_sentences,
            run_on_sentences=run_on_count,
            sentence_fragments=fragment_count,
        )

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _find_location(self, text: str, target: str) -> str:
        """Find approximate location of text."""
        idx = text.find(target)
        if idx < 0:
            return "General content"
        # Find which sentence contains it
        before = text[:idx]
        sentence_num = len(re.findall(r'(?<=[.!?])\s+', before)) + 1
        return f"Sentence {sentence_num}"
