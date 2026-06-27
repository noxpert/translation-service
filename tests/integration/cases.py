"""Hungarian → English test cases for the live-Ollama integration suite.

Source language is always Hungarian (``hu``) and target language English (``en``).
The Karinthy cases (accent-stripping, double-letter typos, one agglutinated noun) are
drawn from Frigyes Karinthy's *Tanár úr kérem*. The extended cases target failure modes
that translation-tuned LLMs are known to struggle with: vowel-harmony violations,
definite vs. indefinite object conjugation, case-suffix stacking, closed-compound
word-boundary errors, idioms, homographs, low-frequency derivational suffixes, and
postpositions.
"""

SOURCE_LANG = "hu"
TARGET_LANG = "en"

# Karinthy long-form strings, reused as expected corrections for misspelled variants.
_CLAUSE_CORRECT = (
    "annak jeléül, hogy az a vegyület, melyről a tanár úr be akarta bizonyítani, "
    "hogy zöldre festi a lángot, a lángot csakugyan zöldre festette"
)
_SENTENCE_CORRECT = (
    "Az ablakok tárva-nyitva voltak a meleg márciusi napon s a friss tavaszi "
    "szellő szárnyán berepült a muzsika a tanterembe."
)

# Extended reference strings for proverb/idiom validate cases.
_PROVERB_CORRECT = "Aki másnak vermet ás, maga esik bele."
_IDIOM_SENTENCE_CORRECT = "Ne igyál előre a medve bőrére."


# --- /validate ---------------------------------------------------------------
#
# Each case carries the input text, whether we expect it to be judged valid,
# and (for invalid inputs) the correctly-spelled text that must appear among the
# returned corrections.
#
# Fields:
#   correct_text  — single gold string; the test passes only when this exact
#                   string (after normalize_correction) appears in corrections.
#   correct_texts — list of acceptable alternatives; the test passes when ANY
#                   entry (after normalize_correction) appears in corrections.
#                   Use instead of correct_text when more than one correction
#                   would be linguistically valid.  Leave both absent (None) for
#                   cases where is_valid is expected to be True.

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

    # --- Extended cases: vowel harmony, j/ly, ö/o swap, compounds, geminates ---

    # Vowel harmony: "-ban" (back suffix) must not attach to front-vowel stem "kert".
    {"id": "vowel-harmony-ok", "text": "a kertben", "expected_valid": True,
     "correct_text": None},
    {"id": "vowel-harmony-violation", "text": "a kertban", "expected_valid": False,
     "correct_text": "a kertben"},

    # ly/j confusion: "mijen" is a phonological misspelling of "milyen".
    {"id": "milyen-ok", "text": "milyen szép", "expected_valid": True,
     "correct_text": None},
    {"id": "milyen-jconfusion", "text": "mijen szép", "expected_valid": False,
     "correct_text": "milyen szép"},

    # ö/o swap strips required front rounded vowels from "gyönyörű".
    {"id": "ou-ok", "text": "gyönyörű kilátás", "expected_valid": True,
     "correct_text": None},
    {"id": "ou-swap", "text": "gyonyoru kilátás", "expected_valid": False,
     "correct_text": "gyönyörű kilátás"},

    # Closed compound written with an erroneous internal space.
    {"id": "compound-ok", "text": "vasútállomás", "expected_valid": True,
     "correct_text": None},
    {"id": "compound-spaced", "text": "vasút állomás", "expected_valid": False,
     "correct_text": "vasútállomás"},

    # Geminate consonant dropped on a verb, altering the word.
    {"id": "geminate-ok", "text": "megcsinálta", "expected_valid": True,
     "correct_text": None},
    {"id": "geminate-dropped", "text": "megcsinálata", "expected_valid": False,
     "correct_text": "megcsinálta"},

    # Proverb: correct vs. two accent slips inside a fixed idiomatic phrase.
    {"id": "proverb-ok", "text": _PROVERB_CORRECT, "expected_valid": True,
     "correct_text": None},
    {"id": "proverb-misspelled",
     "text": "Aki másnak vermet as, maga esik belle.",
     "expected_valid": False, "correct_text": _PROVERB_CORRECT},

    {"id": "idiom-sentence-ok", "text": _IDIOM_SENTENCE_CORRECT,
     "expected_valid": True, "correct_text": None},
    {"id": "idiom-sentence-misspelled",
     "text": "Ne igyal elore a medve borere.",
     "expected_valid": False, "correct_text": _IDIOM_SENTENCE_CORRECT},
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

    # --- Extended cases: conjugation, derivation, suffix stacking, idioms, homographs ---

    # Definite ("látom" — I see it/him/her) vs. indefinite ("látok" — I see something).
    {"id": "latom-definite", "text": "látom", "is_phrase": False,
     "expected_root": "látni",
     "keywords": ["see it", "see him", "see her", "i see"],
     "notes_must_mention": ["definite"]},
    {"id": "latok-indefinite", "text": "látok", "is_phrase": False,
     "expected_root": "látni",
     "keywords": ["see", "i see"],
     "notes_must_mention": ["indefinite"]},

    # Causative derivation: "olvastatja" = "has [someone] read [something]".
    {"id": "olvastat-causative", "text": "olvastatja", "is_phrase": False,
     "expected_root": "olvastatni",
     "keywords": ["has", "have", "makes", "causes", "have him read", "have her read"],
     "notes_must_mention": ["causative"]},

    # Frequentative derivation: "járogat" = "to go/walk around repeatedly".
    {"id": "jarogat-frequentative", "text": "járogat", "is_phrase": False,
     "expected_root": "járogatni",
     "keywords": ["walks around", "goes now and then", "wanders", "frequent",
                  "keeps going", "goes repeatedly", "going repeatedly", "goes around",
                  "walks repeatedly", "repeatedly"],
     "notes_must_mention": ["frequentative", "habitual", "repeated"]},

    # Case-suffix stacking: "házaiban" = ház + -ai (plural possessive) + -ban (inessive).
    # Accept slash notation ("his/her/their") that Claude produces per prompt instruction.
    {"id": "hazaiban-stacked", "text": "házaiban", "is_phrase": False,
     "expected_root": "ház",
     "keywords": ["in his houses", "in her houses", "in their houses", "in the houses",
                  "in his/her", "his/her/their"]},

    # Dense suffix stack: leg- + szép + -bb + -jei + -t (superlative, possessive, accusative).
    {"id": "legszebbjeit-stacked", "text": "legszebbjeit", "is_phrase": False,
     "expected_root": "szép",
     "keywords": ["most beautiful", "the most beautiful ones", "the prettiest"]},

    # Closed compound: "anyanyelv" = "mother tongue", not "anya" + "nyelv" read separately.
    {"id": "anyanyelv-compound", "text": "anyanyelv", "is_phrase": False,
     "expected_root": None,
     "keywords": ["mother tongue", "native language", "first language"]},

    # Idiom: "Ne igyál előre a medve bőrére" ≈ "don't count your chickens before they hatch".
    {"id": "medve-bor-idiom", "text": _IDIOM_SENTENCE_CORRECT, "is_phrase": True,
     "expected_root": None,
     "keywords": ["count your chickens", "premature", "presume", "assume",
                  "before it happens", "get ahead of"]},

    # Proverb: "whoever digs a pit for another falls in himself" ≈ "what goes around…".
    {"id": "vermet-as-proverb", "text": _PROVERB_CORRECT, "is_phrase": True,
     "expected_root": None,
     "keywords": ["comes around", "own grave", "backfire", "trap", "pit"]},

    # Homograph: "vár" alone is ambiguous (noun "castle" or verb "to wait").
    {"id": "var-homograph-bare", "text": "vár", "is_phrase": False,
     "expected_root": None,
     "keywords": ["castle", "wait", "waits", "fort", "fortress"],
     "notes_must_mention": ["castle", "wait", "ambiguous", "context"]},

    # Same homograph resolved by minimal context "a király vára" → castle.
    {"id": "var-homograph-resolved", "text": "a király vára", "is_phrase": True,
     "expected_root": None,
     "keywords": ["castle", "king's castle", "the king's fort"]},

    # Postposition: "a ház mellett" = "next to / beside the house".
    {"id": "postposition-mellett", "text": "a ház mellett", "is_phrase": True,
     "expected_root": None,
     "keywords": ["next to the house", "beside the house", "by the house"]},
]
