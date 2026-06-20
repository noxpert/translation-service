"""Hungarian → English test cases for the live-Ollama integration suite.

Source language is always Hungarian (``hu``) and target language English (``en``).
The sentences are drawn from Frigyes Karinthy's *Tanár úr kérem*.
"""

SOURCE_LANG = "hu"
TARGET_LANG = "en"

# The fully-correct long clause and sentence, reused as the expected correction
# for their misspelled variants below.
_CLAUSE_CORRECT = (
    "annak jeléül, hogy az a vegyület, melyről a tanár úr be akarta bizonyítani, "
    "hogy zöldre festi a lángot, a lángot csakugyan zöldre festette"
)
_SENTENCE_CORRECT = (
    "Az ablakok tárva-nyitva voltak a meleg márciusi napon s a friss tavaszi "
    "szellő szárnyán berepült a muzsika a tanterembe."
)


# --- /validate ---------------------------------------------------------------
#
# Each case carries the input text, whether we expect it to be judged valid,
# and (for invalid inputs) the correctly-spelled text that must appear among the
# returned corrections.

VALIDATE_CASES = [
    {"id": "haromnegyed-ok", "text": "Háromnegyed egykor", "expected_valid": True,
     "correct_text": None},
    {"id": "haromnegyed-noaccent", "text": "Haromnegyed egykor", "expected_valid": False,
     "correct_text": "Háromnegyed egykor"},
    {"id": "termeszetrajzi-wrongaccent", "text": "térmészétrajzi", "expected_valid": False,
     "correct_text": "természetrajzi"},
    {"id": "termeszetrajzi-ok", "text": "természetrajzi", "expected_valid": True,
     "correct_text": None},
    {"id": "termeszetrajzi-misspelled", "text": "termesetrajzi", "expected_valid": False,
     "correct_text": "természetrajzi"},
    {"id": "katedraasztalan-ok", "text": "katedraasztalán", "expected_valid": True,
     "correct_text": None},
    {"id": "katedraasztalan-noaccent", "text": "katedraasztalan", "expected_valid": False,
     "correct_text": "katedraasztalán"},
    {"id": "katedrasztalan-missing", "text": "katedrasztalan", "expected_valid": False,
     "correct_text": "katedraasztalán"},
    {"id": "clause-misspelled",
     "text": (
         "annak jeléül, hogy az a vegyulet, melyröl a tanár úr be akarta bizonyítani, "
         "hogy zöldre festi a lángot, a lángot csakugyan zöldre festete"
     ),
     "expected_valid": False, "correct_text": _CLAUSE_CORRECT},
    {"id": "clause-ok", "text": _CLAUSE_CORRECT, "expected_valid": True,
     "correct_text": None},
    {"id": "sentence-ok", "text": _SENTENCE_CORRECT, "expected_valid": True,
     "correct_text": None},
    {"id": "sentence-misspelled",
     "text": (
         "Az ablakok tárva-nyitva voltak a melleg márciusi napon s a fris tavaszi "
         "szellő szárnyán berepult a muzsika a tanterembe."
     ),
     "expected_valid": False, "correct_text": _SENTENCE_CORRECT},
]


# --- /translate --------------------------------------------------------------
#
# ``expected_root`` is the lemma we expect in ``root_source`` (``None`` when the
# input is a phrase/clause or already a lemma, in which case the API returns a
# null root). ``keywords`` are English words; the translation check passes when
# any of them appears in ``target_text`` (case-insensitive).

TRANSLATE_CASES = [
    {"id": "haromnegyed", "text": "Háromnegyed egykor", "is_phrase": True,
     "expected_root": None, "keywords": ["quarter"]},
    {"id": "termeszetrajzi", "text": "természetrajzi", "is_phrase": False,
     "expected_root": None, "keywords": ["natural"]},
    {"id": "katedraasztalan", "text": "katedraasztalán", "is_phrase": False,
     "expected_root": "katedraasztal",
     "keywords": ["desk", "table", "lectern", "podium", "cathedra", "teacher"]},
    {"id": "clause", "text": _CLAUSE_CORRECT, "is_phrase": True,
     "expected_root": None, "keywords": ["flame", "green"]},
    {"id": "sentence", "text": _SENTENCE_CORRECT, "is_phrase": True,
     "expected_root": None, "keywords": ["window"]},
    {"id": "paragraph",
     "text": (
         "Háromnegyed egykor, ép abban a pillanatban, mikor a természetrajzi terem "
         "katedraasztalán hosszú és sikertelen kísérletek után végre-valahára, "
         "nagynehezen, izgatott várakozás jutalmául a Bunsen-lámpa színtelen lángjában "
         "fellobbant egy gyönyörű, smaragdzöld csík, annak jeléül, hogy az a vegyület, "
         "melyről a tanár úr be akarta bizonyítani, hogy zöldre festi a lángot, a lángot "
         "csakugyan zöldre festette, mondom: pont háromnegyed egykor, ép ebben a "
         "diadalmas minutumban megpendült a szomszéd ház udvarán egy zongora-verkli s "
         "ezzel minden komolyságnak egyszeribe vége szakadt. Az ablakok tárva-nyitva "
         "voltak a meleg márciusi napon s a friss tavaszi szellő szárnyán berepült a "
         "muzsika a tanterembe."
     ),
     "is_phrase": True, "expected_root": None,
     "keywords": ["quarter", "flame", "window", "music"]},
]
