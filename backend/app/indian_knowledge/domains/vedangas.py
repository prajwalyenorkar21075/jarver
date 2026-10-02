"""Six Vedangas — Shiksha, Kalpa, Vyakarana, Nirukta, Chandas, Jyotisha."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_vedangas_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="vedangas",
        description="The six Vedangas (limbs of the Veda) — auxiliary disciplines required for proper understanding and application of Vedic knowledge. They cover phonetics, ritual, grammar, etymology, prosody, and astronomy.",
        subcategories=["shiksha", "kalpa", "vyakarana", "nirukta", "chandas", "jyotisha"],
        metadata={"tradition": "Hindu", "purpose": "Auxiliary sciences for Vedic study"},
    )

    domain.add_entry(KnowledgeEntry(
        id="vedanga-shiksha-001",
        title="Shiksha — The Science of Phonetics and Pronunciation",
        content="""Shiksha (शिक्षा) is the Vedanga dealing with phonetics, pronunciation, and the proper articulation of Vedic mantras. It is considered the "nose" of the Vedic Purusha — essential for the "breath" of the sacred word.

Core Subject Matter:
- Varna (varṇa): The classification and production of Sanskrit sounds
  - Svara (vowels): a, ā, i, ī, u, ū, ṛ, ṝ, ḷ, e, ai, o, au
  - Vyanjana (consonants): Organized into five vargas (ka-varga to ma-varga) plus semivowels, sibilants, and aspirates
  - Anunasika (nasal sounds) and Visarga (ḥ)
- Svara (accent): The three Vedic pitch accents — Udatta (high), Anudatta (low), Svarita (falling)
- Matra (quantity): Duration of syllable pronunciation — hrasva (short), dirgha (long), pluta (extended)
- Bala (strength): The force or emphasis with which syllables are pronounced
- Sama (continuity): The smooth, even flow of connected speech
- Santana (connection): The proper joining of words in continuous recitation (sandhi)

Why It Matters:
- Vedic mantras must be pronounced exactly — even a slight error changes the meaning
- The power of the mantra lies in its sound (shabda), not just its meaning
- Incorrect pronunciation is said to produce opposite results or no results at all
- Each sound has a specific place of articulation (sthana), effort (prayatna), and resonance

Key Texts:
- Paniniya Shiksha (associated with Panini's grammar)
- Yajnavalkya Shiksha
- Naradiya Shiksha
- Bharadvaja Shiksha""",
        domain="vedangas",
        category="shiksha",
        tags=["shiksha", "phonetics", "pronunciation", "sanskrit", "mantra", "vedic accents"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "The word 'asura' pronounced with Udatta on 'a' means 'demon'; with Udatta on 'u' it means 'non-sun' — completely different meanings",
            "Sandhi rules: 'na u' becomes 'no', 'iti' after 'a' becomes 'eti' — proper joining is essential",
            "The shiksha text classifies sounds by place: Kanthya (throat), Talavya (palate), Murdhanya (retroflex), Dantya (teeth), Oshthya (lips)",
        ],
        references=[
            "Shiksha is called the 'nose' of the Vedapurusha — the organ of breath and smell",
            "Panini's Ashtadhyayi (grammar) presupposes knowledge of Shiksha",
            "The oral tradition of the Vedas has preserved pronunciation with remarkable accuracy for over 3,000 years",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="vedanga-kalpa-001",
        title="Kalpa — The Science of Vedic Ritual and Ceremony",
        content="""Kalpa (कल्प) is the Vedanga dealing with ritual procedures — the "hands" of the Vedic Purusha. It provides systematic, concise rules (sutras) for performing Vedic ceremonies correctly.

Three Main Divisions:

1. Shrauta Sutras (श्रौत सूत्र):
   - Deal with the great Vedic sacrifices (shrauta) that require three sacred fires
   - Based on the Shruti (revealed texts — the Vedas themselves)
   - Elaborate public rituals: Agnihotra, Darshapurnamasa, Chaturmasya, Soma sacrifices, Ashvamedha, Rajasuya
   - Require trained priests: Hotri, Adhvaryu, Udgatri, Brahma
   - Baudhayana, Apastamba, Katyayana, and Latyayana Shrauta Sutras

2. Grihya Sutras (गृह्य सूत्र):
   - Deal with domestic rituals performed by householders
   - Based on Smriti (tradition) rather than Shruti
   - Samskaras (life-cycle sacraments): Garbhadhana (conception), Jatakarma (birth), Namakarana (naming), Annaprashana (first food), Upanayana (sacred thread), Vivaha (marriage), Antyeshti (funeral)
   - Pancha Mahayajna: Five daily duties — Brahma (study), Deva (worship), Pitri (ancestors), Bhuta (beings), Manushya (humans)
   - Seasonal observances and household fire rituals

3. Dharma Sutras (धर्म सूत्र):
   - Deal with law, ethics, social conduct, and duties
   - Later expanded into Dharma Shastras (e.g., Manusmriti)
   - Cover varnashrama dharma (duties by caste and life stage)
   - Rules for kings, justice, penance, purification
   - Baudhayana, Apastamba, Gautama, and Vashishtha Dharma Sutras

The Kalpa Sutras are written in extremely concise aphoristic style (sutra = thread) — each word is precious and requires commentary (bhashya) for understanding.""",
        domain="vedangas",
        category="kalpa",
        tags=["kalpa", "ritual", "ceremony", "samskara", "shrauta", "grihya", "dharma"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "Upanayana (sacred thread ceremony): The boy receives the yajnopavita (sacred thread), a guru is accepted, and Gayatri mantra is taught — marking the beginning of Vedic study",
            "Agnihotra: Daily morning and evening fire offering — milk, grain, or ghee offered to Agni with specific mantras",
            "Vivaha (marriage): Seven steps around the sacred fire (saptapadi), each step with a specific mantra and blessing",
            "Antyeshti (funeral): The body is cremated, the soul released, and shraddha ceremonies performed for 13 days",
        ],
        references=[
            "Kalpa is called the 'hands' of the Vedapurusha — the organ of action",
            "The Kalpa Sutras are associated with specific Vedic schools (charana)",
            "Baudhayana Sulba Sutra contains geometric rules for altar construction — early Indian mathematics",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="vedanga-vyakarana-001",
        title="Vyakarana — The Science of Grammar and Linguistic Analysis",
        content="""Vyakarana (व्याकरण) is the Vedanga dealing with grammar — the "mouth" of the Vedic Purusha, the organ of speech. It provides the rules for correct Sanskrit, ensuring the purity of the sacred language.

The Great Grammarian — Panini:
- Panini's Ashtadhyayi (Eight Chapters) — composed c. 4th century BCE
- 3,996 sutras (rules) organized into 8 chapters, each divided into 4 padas (sections)
- The most comprehensive and sophisticated grammar of the ancient world
- Covers phonetics, morphology, syntax, semantics, and word-formation
- Uses a meta-language of technical terms and abbreviations
- Generative in nature — from roots (dhatu) and suffixes (pratyaya), all words can be derived

Key Concepts:
- Dhatu (धातु): Verbal roots — approximately 2,000 roots from which all words derive
- Prakriti (प्रकृति): The base or original form of a word
- Pratyaya (प्रत्यय): Suffixes that modify the base to create new words
- Sandhi (सन्धि): Rules for the combination of sounds at word boundaries
- Samasa (समास): Compound words — Dvandva, Tatpurusha, Bahuvrihi, Avyayibhava, Karmadharaya
- Vibhakti (विभक्ति): Case endings — 7 cases plus vocative
- Lakara (लकार): Verb tenses and moods — 10 classes of verbs

Why Grammar Matters for the Vedas:
- Correct grammar ensures correct meaning of mantras
- Sanskrit is a highly inflected language — endings change meaning
- Panini's rules capture the structure of the entire language
- "The mouth of the Vedas" — without grammar, the Vedas cannot be properly understood

Post-Paninian Developments:
- Katyayana's Varttikas (comments on Panini)
- Patanjali's Mahabhashya (Great Commentary) — the definitive work
- Bhartrihari's Vakyapadiya — philosophy of language and the theory of Sphota (the word as a whole)""",
        domain="vedangas",
        category="vyakarana",
        tags=["vyakarana", "grammar", "panini", "sanskrit", "linguistics", "ashtadhyayi"],
        difficulty=DifficultyLevel.ADVANCED,
        examples=[
            "Root 'kṛ' (to do) → karoti (he does), akārayat (he caused to do), kartā (doer), karma (action/deed), kriyā (action)",
            "Sandhi: 'deva + ālayaḥ' → 'devālayaḥ' (temple, literally 'god's house')",
            "Compound: 'rājapuruṣaḥ' (Tatpurusha) = 'rājñaḥ puruṣaḥ' = 'the king's man'",
            "Panini's rule: 'vṛddhir ādaiC' — defines the technical term 'vṛddhi' as the vowels ā, ai, au",
        ],
        references=[
            "Vyakarana is called the 'mouth' of the Vedapurusha — the organ of speech",
            "Panini's grammar is considered one of the greatest intellectual achievements of ancient India",
            "Paniniya Shiksha (phonetics) is the companion text to Vyakarana",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="vedanga-nirukta-001",
        title="Nirukta — The Science of Etymology and Word Interpretation",
        content="""Nirukta (निरुक्त) is the Vedanga dealing with etymology and the interpretation of Vedic words — the "ear" of the Vedic Purusha. It explains the meaning and derivation of difficult Vedic terms.

The Foundational Text:
- Yaska's Nirukta (c. 6th-5th century BCE)
- Commentary on the Nighantu (Vedic glossary of approximately 1,800 words)
- Organized into 3 sections: Naighantuka (synonyms), Naigama (homonyms), Daivata (deities)
- Provides etymological analysis of each word, tracing it back to its verbal root (dhatu)

Method of Etymology (Nirvacana):
- Every word is analyzed as derived from a verbal root
- The meaning is explained through the root + affixes
- Example: 'Indra' = 'indha' (he who kindles/illuminates) from root 'indh'
- Example: 'Varuna' = 'vr' (to cover) — the one who envelops
- Example: 'Agni' = 'agri' (the foremost/leader) — fire as the leader of rituals

Why Etymology Matters:
- Vedic Sanskrit contains archaic words no longer in common use
- The meaning of mantras depends on precise word interpretation
- Etymology reveals the deeper, symbolic meaning behind names of deities
- Connects words to their conceptual roots — understanding the "why" behind naming
- Preserves the original semantic field of Vedic vocabulary

Key Principles:
- Words are not arbitrary — they have an inherent relationship with their meaning
- The same concept can be expressed by different words, each highlighting a different aspect
- Deity names describe their functions and qualities, not just labels
- Etymology is a tool for meditation — understanding the nature of reality through language""",
        domain="vedangas",
        category="nirukta",
        tags=["nirukta", "etymology", "yaska", "word meaning", "vedic interpretation", "nighantu"],
        difficulty=DifficultyLevel.ADVANCED,
        examples=[
            "Yaska explains 'Surya' (sun): from 'sṛ' (to move) — 'the one who moves across the sky'",
            "'Usha' (dawn): from 'vas' (to shine) — 'the one who shines forth'",
            "'Vāc' (speech): from 'vac' (to speak) — speech is identified with its function",
            "Nirukta 1.1: 'The gods are known through mantras, and mantras through the Nighantu and Nirukta'",
        ],
        references=[
            "Nirukta is called the 'ear' of the Vedapurusha — the organ of hearing meaning",
            "Yaska is considered the first etymologist in world history",
            "Nirukta is essential for understanding the Rig Veda's archaic vocabulary",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="vedanga-chandas-001",
        title="Chandas — The Science of Vedic Meter and Prosody",
        content="""Chandas (छन्दस्) is the Vedanga dealing with poetic meter and prosody — the "feet" of the Vedic Purusha. It governs the rhythmic structure of Vedic hymns, ensuring they are recited with the correct cadence.

Vedic Meters (Chhandas):
The Vedas use specific meters, each with a fixed number of syllables per line (pada) and a fixed number of lines per stanza (rich):

1. Gayatri (गायत्री): 3 padas × 8 syllables = 24 syllables
   - The most sacred meter. The Gayatri Mantra is in this meter.
   - Associated with the Rig Veda and the morning invocation

2. Tristubh (त्रिष्टुभ्): 3 padas × 11 syllables = 33 syllables (sometimes 4 padas)
   - The most common meter in the Rig Veda
   - Used for hymns to Indra, Agni, and other major deities

3. Jagati (जगती): 4 padas × 12 syllables = 48 syllables
   - Longer, more expansive meter
   - Used for hymns requiring extended expression

4. Anushtubh (अनुष्टुभ्): 4 padas × 8 syllables = 32 syllables
   - The meter of the Atharva Veda and the epics (Mahabharata, Ramayana)
   - Also called Shloka — the standard epic meter

5. Pankti (पंक्ति): 5 padas × 8 syllables = 40 syllables
   - Less common, used in specific ritual contexts

6. Brihati (बृहती): 4 padas with 8+8+12+8 = 36 syllables
   - Asymmetric meter used in Brahmana texts

Why Meter Matters:
- The rhythmic pattern creates a specific vibrational effect
- Each meter has a deity associated with it
- The meter determines the musical quality when chanted
- Correct meter preserves the oral tradition across generations
- The syllable count and stress pattern create the mantra's shakti (power)

Key Texts:
- Pingala's Chhandas Shastra (later, but foundational for classical prosody)
- The Anukramanis (indexes) that record the meter of each Rig Vedic hymn""",
        domain="vedangas",
        category="chandas",
        tags=["chandas", "meter", "prosody", "gayatri", "trishtubh", "vedic poetry", "rhythm"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "Gayatri Mantra meter: 'Om Bhur Bhu-vah Svah' (8) | 'Tat Sa-vi-tur Va-re-nyam' (8) | 'Bhar-go De-vas-ya Dhi-ma-hi' (8) — 3 lines of 8 syllables each",
            "Rig Veda 1.1.1 in Tristubh: 'A-gnim ī-le pu-ro-hi-tam' (11) | 'ya-jñai-sya de-vam ṛ-tvi-jam' (11) | 'ho-tā-ram rat-na-dhā-ta-mam' (11)",
            "The word 'Chhandas' itself comes from 'chad' (to cover) — meter covers/embellishes the meaning with rhythm",
        ],
        references=[
            "Chandas is called the 'feet' of the Vedapurusha — the organ of movement and rhythm",
            "The Rig Veda uses primarily Gayatri, Tristubh, and Jagati meters",
            "Pingala's Chhandas Shastra (c. 3rd-2nd century BCE) is the foundational text on prosody and contains early binary number systems",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="vedanga-jyotisha-001",
        title="Jyotisha — The Science of Astronomy and Time-Reckoning",
        content="""Jyotisha (ज्योतिष) is the Vedanga dealing with astronomy and calendrical science — the "eye" of the Vedic Purusha. It provides the knowledge needed to determine the correct times for performing Vedic rituals.

Purpose and Scope:
- Determining the appropriate times (muhurta) for rituals and sacrifices
- Tracking the movements of the sun and moon
- Calculating the lunar months and intercalary months (adhika masa)
- Observing the nakshatras (lunar mansions/stars)
- Creating the Vedic calendar (panchanga)

Key Concepts:

The Vedic Calendar:
- Based on the lunar-solar system
- 12 lunar months (masa), each divided into two pakshas (fortnights): Shukla (waxing) and Krishna (waning)
- 30 tithis (lunar days) per month
- Intercalary month (Adhika Masa) added every 2-3 years to align lunar and solar years
- 6 ritus (seasons): Vasanta (spring), Grishma (summer), Varsha (monsoon), Sharad (autumn), Hemanta (pre-winter), Shishira (winter)

Nakshatras (Lunar Mansions):
- 27 (or 28) nakshatras dividing the ecliptic
- Each ruled by a deity and associated with specific qualities
- The moon passes through one nakshatra per day
- Key nakshatras: Krittika (Pleiades), Rohini, Mrigashira, Pushya, Ashadha, Shravana, Dhanishtha

Vedanga Jyotisha of Lagadha:
- The oldest extant text on Indian astronomy (c. 1350-1150 BCE)
- Describes a 5-year yuga (cycle) with 62 lunar months and 1830 days
- Tracks the sun and moon through the nakshatras
- Provides rules for determining the beginning of months and seasons
- Uses water clocks (clepsydra) for time measurement

Why Astronomy Matters for the Vedas:
- Rituals must be performed at astronomically determined times
- The new moon (Amavasya) and full moon (Purnima) mark key ritual days
- Solstices (Ayana) and equinoxes (Vishuva) are ritually significant
- The cosmic order (rita) is reflected in celestial regularity""",
        domain="vedangas",
        category="jyotisha",
        tags=["jyotisha", "astronomy", "calendar", "nakshatra", "time", "vedic calendar", "lagadha"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "The 5-year Yuga: 60 months, 1,830 days, 1,835 lunar mansions — a complete cycle of sun-moon alignment",
            "Pushya nakshatra is considered the most auspicious for beginning new ventures and rituals",
            "Adhika Masa (extra month): When the solar and lunar calendars diverate, an extra month is inserted — 'Purushottama Masa' is considered sacred",
            "The Vedanga Jyotisha describes the solstitial points moving through nakshatras — early observation of precession",
        ],
        references=[
            "Jyotisha is called the 'eye' of the Vedapurusha — the organ of sight and time-perception",
            "Vedanga Jyotisha is attributed to the sage Lagadha",
            "This Vedanga later evolved into the full science of Jyotish Shastra (Indian astrology/astronomy) with Siddhantas",
        ],
    ))

    return domain
