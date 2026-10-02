"""Vedic Literature — Upanishads, Brahmanas, and Aranyakas."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_vedic_literature_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="vedic_literature",
        description="The Vedic corpus — Upanishads (philosophy and spiritual thought), Brahmanas (rituals and ceremonies), and Aranyakas (meditation and contemplation). The foundational texts of Hindu philosophy and spiritual tradition.",
        subcategories=["upanishads", "brahmanas", "aranyakas", "vedas", "philosophy"],
        metadata={"tradition": "Hindu", "language": "Sanskrit", "period": "1500-500 BCE"},
    )

    domain.add_entry(KnowledgeEntry(
        id="vedic-upanishads-001",
        title="Upanishads — The Philosophical Core of Vedic Thought",
        content="""The Upanishads are the philosophical and spiritual culmination of the Vedas, also known as Vedanta (literally "sitting down near" a teacher, or the "end of the Vedas"). They represent the transition from external ritual to internal spiritual inquiry.

Core Teachings:
- Brahman: The ultimate reality, the absolute, the ground of all existence — formless, infinite, eternal
- Atman: The true self or soul within each being — identical with Brahman in essence
- Tat Tvam Asi: "Thou art that" — the identity of individual self with universal reality
- Maya: The illusory nature of the phenomenal world that veils the ultimate reality
- Moksha: Liberation from the cycle of birth and death (samsara) through Self-realization

Key Themes:
- The nature of reality and consciousness
- The relationship between individual self (Atman) and universal self (Brahman)
- Methods of meditation and self-inquiry
- The path to liberation (moksha)
- The unity of all existence

The Upanishads are shruti (revealed) texts, considered eternal truths heard by ancient rishis (seers) in deep meditation.""",
        domain="vedic_literature",
        category="upanishads",
        tags=["upanishads", "philosophy", "brahman", "atman", "vedanta", "moksha", "spiritual"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "Maha Vakya (Great Sayings): 'Tat Tvam Asi' (That thou art), 'Aham Brahmasmi' (I am Brahman), 'Prajnanam Brahma' (Consciousness is Brahman)",
            "The analogy of salt in water: Atman pervades the body as salt pervades water — invisible but present everywhere",
            "The chariot analogy (Katha Upanishad): Body is the chariot, senses are horses, mind is the reins, intellect is the charioteer, Atman is the rider",
        ],
        references=[
            "There are 108 Mukhya (principal) Upanishads",
            "10 are considered most important: Isha, Kena, Katha, Prashna, Mundaka, Mandukya, Taittiriya, Aitareya, Chandogya, Brihadaranyaka",
            "Commentaries by Adi Shankara, Ramanuja, and Madhva form the basis of Vedanta philosophy",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="vedic-upanishads-002",
        title="Major Upanishads — The Ten Principal Texts",
        content="""The ten principal (Mukhya) Upanishads are the oldest and most authoritative, embedded within the four Vedas:

Rig Veda:
- Aitareya Upanishad: Deals with the nature of the self and creation. Describes the creation of the world and the entry of Atman into the body.

Sama Veda:
- Kena Upanishad: Explores the nature of Brahman through the question "By whom does the mind think?" Teaches that Brahman is the source behind all senses and mind.
- Chandogya Upanishad: One of the longest. Contains the famous "Tat Tvam Asi" teaching. Discusses Om, the nature of reality, and the story of Satyakama Jabala.

Yajur Veda (Shukla):
- Brihadaranyaka Upanishad: The largest and oldest. Comprehensive treatment of Brahman, Atman, creation, meditation, and philosophy. Contains Yajnavalkya's dialogues.
- Isha Upanishad: Brief but profound. Opens with the teaching that all this is pervaded by the Lord. Teaches the harmony of knowledge and action.
- Taittiriya Upanishad: Describes the five koshas (sheaths) of the self — Annamaya, Pranamaya, Manomaya, Vijnanamaya, Anandamaya.

Atharva Veda:
- Prashna Upanishad: Six questions asked by six students to the sage Pippalada. Covers prana, meditation, Om, and the nature of the self.
- Mundaka Upanishad: Distinguishes between higher knowledge (Brahman) and lower knowledge (rituals). Famous for the "two birds" analogy.
- Mandukya Upanishad: Shortest but most profound. Analyzes the four states of consciousness — waking, dreaming, deep sleep, and Turiya (the fourth).
- Katha Upanishad: The story of Nachiketa and Yama (Death). Teaches the nature of Atman, the path to liberation, and the famous chariot analogy.""",
        domain="vedic_literature",
        category="upanishads",
        tags=["upanishads", "ten principal", "brihadaranyaka", "chandogya", "katha", "mundaka", "mandukya"],
        difficulty=DifficultyLevel.ADVANCED,
        prerequisites=["vedic-upanishads-001"],
        examples=[
            "Mandukya's four states: Waking (Vaishvanara), Dreaming (Taijasa), Deep Sleep (Prajna), Turiya (the silent witness beyond all three)",
            "Mundaka's two birds: Two birds on the same tree — one eats the fruit (experiencing world), the other watches (the witness Self)",
            "Taittiriya's five koshas: Food sheath (body), Vital air sheath (prana), Mental sheath (mind), Intellectual sheath (buddhi), Bliss sheath (ananda)",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="vedic-brahmanas-001",
        title="Brahmanas — The Ritual Texts of the Vedas",
        content="""The Brahmanas are prose texts that explain and elaborate upon the Vedic hymns (mantras), providing detailed instructions for performing Vedic rituals (yajnas). They serve as the ritual handbook of the Vedic period.

Purpose and Content:
- Detailed explanation of Vedic rituals and ceremonies
- The mythology and stories behind each ritual
- The symbolic meaning of ritual actions
- Instructions for priests (hotri, adhvaryu, udgatri, brahman)
- The cosmic significance of sacrificial acts
- The connection between ritual action and cosmic order (rita)

The Four Brahmanas:
- Aitareya Brahmana (Rig Veda): Deals with the Soma sacrifice and the consecration of kings
- Taittiriya Brahmana (Krishna Yajur Veda): Contains ritual procedures and the story of Shunahshepa
- Shatapatha Brahmana (Shukla Yajur Veda): The most comprehensive. "Hundred Paths" — extensive ritual details and the flood story of Manu
- Tandya Mahabrahmana (Sama Veda): Also called Panchavimsha Brahmana. Contains Soma rituals and chants

Key Concepts:
- Yajna (sacrifice): The central act that maintains cosmic order
- Rita: Cosmic order and truth that sustains the universe
- Brahman (in ritual context): The sacred word/prayer that has cosmic power
- The identification of ritual with cosmic processes
- Prajapati: The creator god identified with the sacrifice itself""",
        domain="vedic_literature",
        category="brahmanas",
        tags=["brahmanas", "rituals", "yajna", "sacrifice", "vedic ceremonies", "soma"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "Ashvamedha: The horse sacrifice — a king's ritual to assert sovereignty. The horse roams free for a year, followed by warriors",
            "Agnihotra: Daily fire ritual performed twice a day at dawn and dusk with offerings of milk and grain",
            "Soma Yajna: Elaborate multi-day ritual involving the extraction and offering of the Soma plant's juice",
            "Purushamedha: The symbolic sacrifice of the cosmic being (Purusha) whose body parts became the four varnas",
        ],
        references=[
            "Shatapatha Brahmana is the longest — 100 chapters (adhyayas) of ritual instruction",
            "The Brahmanas mark the transition from spontaneous hymn composition to formalized ritual",
            "They were composed approximately 900-700 BCE, after the Samhitas and before the Aranyakas",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="vedic-aranyakas-001",
        title="Aranyakas — The Forest Texts of Meditation and Contemplation",
        content="""The Aranyakas ("forest texts") are the transitional bridge between the external rituals of the Brahmanas and the internal philosophy of the Upanishads. They were composed for hermits and ascetics who had retired to the forest for meditation and spiritual practice.

Nature and Purpose:
- Composed for study in the forest (aranya = forest), away from village life
- Reinterpret external rituals as internal, meditative practices
- Shift from ritual action (karma) to knowledge (jnana)
- Contain both ritual material and philosophical speculation
- Serve as the link between Brahmanas and Upanishads

Key Aranyakas:
- Aitareya Aranyaka (Rig Veda): Contains the Aitareya Upanishad. Discusses the symbolic meaning of the Mahavrata ceremony.
- Taittiriya Aranyaka (Krishna Yajur Veda): Contains the Taittiriya Upanishad. Includes the famous Shikshavalli with the teacher's farewell address.
- Brihad Aranyaka (Shukla Yajur Veda): The "Great Forest Text" — contains the Brihadaranyaka Upanishad. The most extensive.
- Sama Veda Aranyaka: Also called Talavakara Aranyaka. Contains the Kena Upanishad.
- Atharva Veda Aranyakas: Include portions that became major Upanishads.

Philosophical Shift:
- The fire of Agnihotra becomes the fire of digestion and consciousness
- The external altar becomes the internal body
- The sacrificial offerings become breath, thought, and speech
- Ritual precision gives way to contemplative insight
- The universe itself is seen as a continuous sacrifice""",
        domain="vedic_literature",
        category="aranyakas",
        tags=["aranyakas", "forest texts", "meditation", "contemplation", "spiritual study", "transition"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "Internalization of Agnihotra: Instead of offering milk into fire, the practitioner offers food into the digestive fire (jatharagni) within",
            "Prana Agnihotra: Offering each breath into the next breath — breathing as continuous sacrifice",
            "The five fires (Panchagni Vidya): The soul passes through five cosmic fires in the cycle of rebirth — heaven, rain, earth, man, woman",
            "Meditation on Om: The syllable Om contains all the Vedas, all the worlds, all the gods",
        ],
        references=[
            "The Aranyakas were composed approximately 800-600 BCE",
            "They represent the shift from householder ritualism to forest-dweller contemplation",
            "Many Upanishads are embedded within Aranyakas as their concluding portions",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="vedic-vedas-001",
        title="The Four Vedas — Foundation of Indian Knowledge",
        content="""The Vedas are the oldest and most sacred scriptures of Hinduism, considered apaurusheya (not of human origin) — eternal truths revealed to ancient rishis in deep meditation.

The Four Vedas:

1. Rig Veda (Veda of Hymns):
   - Oldest Veda (c. 1500-1200 BCE)
   - 1,028 hymns (suktas) arranged in 10 mandalas (books)
   - Hymns praising deities: Agni, Indra, Varuna, Soma, Surya
   - Contains the Gayatri Mantra and Purusha Sukta
   - Foundation of all other Vedas

2. Sama Veda (Veda of Melodies):
   - Veda of chants and music
   - 1,875 verses, mostly from Rig Veda, set to melody
   - Used by the Udgatri priest during Soma sacrifices
   - Origin of Indian classical music
   - Emphasizes the musical aspect of worship

3. Yajur Veda (Veda of Sacrificial Formulas):
   - Prose mantras and rituals for the Adhvaryu priest
   - Two recensions: Shukla (White) and Krishna (Black)
   - Contains detailed sacrificial procedures
   - Basis of Vedic ritual practice
   - Taittiriya and Vajasaneyi Samhitas

4. Atharva Veda (Veda of Daily Life):
   - Most practical and worldly Veda
   - 731 hymns — spells, charms, medical formulas
   - Daily life concerns: health, prosperity, marriage, death
   - Contains philosophical hymns and speculation
   - Basis of Ayurveda (medicine)

Each Veda has four layers: Samhita (hymns), Brahmana (rituals), Aranyaka (meditation), Upanishad (philosophy).""",
        domain="vedic_literature",
        category="vedas",
        tags=["vedas", "rig veda", "sama veda", "yajur veda", "atharva veda", "scriptures", "sacred texts"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "Gayatri Mantra (Rig Veda 3.62.10): 'Om Bhur Bhuvah Svah, Tat Savitur Varenyam, Bhargo Devasya Dhimahi, Dhiyo Yo Nah Prachodayat'",
            "Purusha Sukta (Rig Veda 10.90): Describes the cosmic being whose sacrifice created the universe and the four varnas",
            "Nasadiya Sukta (Rig Veda 10.129): The creation hymn — 'Then even nothingness was not, nor existence' — profound philosophical speculation",
            "Rudra hymns from Yajur Veda evolved into the worship of Shiva",
        ],
        references=[
            "The Vedas were transmitted orally for millennia before being written down",
            "Veda Vyasa is credited with compiling and dividing the single Veda into four",
            "Each Veda has multiple shakhas (recensions) — only a fraction survive today",
        ],
    ))

    return domain
