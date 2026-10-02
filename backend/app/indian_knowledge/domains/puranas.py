"""Puranas — Traditional and Mythological Knowledge."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_puranas_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="puranas",
        description="The Puranas — ancient narratives of creation, cosmology, genealogy of gods and kings, and the deeds of divine incarnations. They are the encyclopedic literature of Hindu tradition.",
        subcategories=["mahapuranas", "cosmology", "creation", "avatars", "devotion"],
        metadata={"tradition": "Hindu", "language": "Sanskrit", "genre": "Purana (ancient narrative)"},
    )

    domain.add_entry(KnowledgeEntry(
        id="puranas-overview-001",
        title="The Puranas — Structure and Purpose",
        content="""The Puranas (पुराण, "ancient") are a vast genre of Indian literature that cover a wide range of topics — from cosmology and creation myths to genealogies of gods, kings, and sages, to pilgrimage guides and devotional teachings.

The 18 Maha Puranas (Great Puranas):
Traditionally attributed to Vyasa, organized by the three gunas:

Sattvic Puranas (preserving, associated with Vishnu):
1. Vishnu Purana — Comprehensive, focused on Vishnu
2. Bhagavata Purana — The most popular; Krishna's life and teachings
3. Narada Purana — Devotion and pilgrimage
4. Garuda Purana — Death, afterlife, and Vishnu worship
5. Padma Purana — Creation and devotion
6. Varaha Purana — The boar avatar of Vishnu
7. Kurma Purana — The tortoise avatar
8. Matsya Purana — The fish avatar and the great flood
9. Vamana Purana — The dwarf avatar
10. Skanda Purana — The largest; pilgrimage guides and Shiva's son Skanda

Rajasic Puranas (active, associated with Brahma):
11. Brahma Purana — Creation by Brahma
12. Brahmanda Purana — The cosmic egg and creation
13. Brahmavaivarta Purana — Krishna and Radha
14. Markandeya Purana — Contains the Devi Mahatmya (Durga Saptashati)
15. Bhavishya Purana — Prophecies and future ages
16. Vamana Purana (alternate classification)

Tamasic Puranas (associated with Shiva):
17. Shiva Purana — Shiva's glory and teachings
18. Linga Purana — The linga form of Shiva

The Five Characteristics (Pancha Lakshana):
Every Purana traditionally covers five topics:
1. Sarga — Primary creation of the universe
2. Pratisarga — Secondary creation after dissolution
3. Vamsha — Genealogies of gods, sages, and kings
4. Manvantara — The reigns of the Manus (cosmic cycles)
5. Vamshanucharita — Histories of royal dynasties

Purpose:
- Make Vedic philosophy accessible to all, not just scholars
- Teach dharma through stories and narratives
- Inspire devotion (bhakti) to the divine
- Preserve cultural and historical traditions
- Guide pilgrimage and religious practice""",
        domain="puranas",
        category="mahapuranas",
        tags=["puranas", "18 puranas", "vyasa", "vishnu", "shiva", "brahma", "cosmology"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "Bhagavata Purana (Srimad Bhagavatam): The most beloved — 12 books, 18,000 verses, with the 10th book (Krishna's life) being the most celebrated",
            "Shiva Purana: 24,000 verses covering Shiva's marriage to Parvati, the destruction of Daksha's sacrifice, and the descent of the Ganges",
            "Markandeya Purana: Contains the Devi Mahatmya (700 verses) — the foundational text of Shakti worship, describing the Goddess slaying the demon Mahishasura",
            "Vishnu Purana: Considered the most 'classical' and systematic — covers all five traditional topics comprehensively",
        ],
        references=[
            "The Puranas were composed over many centuries (c. 300 BCE - 1000 CE)",
            "They are classified as Smriti (remembered) literature, not Shruti (revealed)",
            "There are also 18 Upa-Puranas (secondary Puranas) and many Sthala Puranas (local temple Puranas)",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="puranas-cosmology-001",
        title="Puranic Cosmology — Creation, Cycles, and the Structure of the Universe",
        content="""The Puranas present a rich cosmological vision of the universe — vast in scale, cyclical in nature, and pervaded by the divine at every level.

Cosmic Cycles (Kala):

The Yugas (Ages):
Time moves in cycles of four Yugas, each shorter and less dharmic than the last:
1. Satya Yuga (Krita Yuga): 1,728,000 years — Golden age, dharma stands on all four legs
2. Treta Yuga: 1,296,000 years — Silver age, dharma stands on three legs
3. Dvapara Yuga: 864,000 years — Bronze age, dharma stands on two legs
4. Kali Yuga: 432,000 years — Iron age, dharma stands on one leg (we are currently in Kali Yuga)

A complete cycle of four Yugas = 4,320,000 years (Maha Yuga)
71 Maha Yugas = 1 Manvantara (reign of one Manu) = 306,720,000 years
14 Manvantaras = 1 Kalpa (day of Brahma) = 4.32 billion years
2 Kalpas = 1 day and night of Brahma
360 days of Brahma = 1 year of Brahma
100 years of Brahma = the full lifespan of Brahma = 311.04 trillion years
After Brahma's life, there is a great dissolution (Mahapralaya) before a new cycle begins.

The Structure of the Universe:

Bhu Mandala (Earth Region):
- Jambu Dvipa: The central island continent, where Bharata Varsha (India) is located
- 6 concentric island continents separated by 6 oceans (salt, sugar cane, wine, ghee, curd, water)
- Each continent is twice the size of the previous one

The Upper Worlds (Lokas):
- Bhur Loka (Earth), Bhuvar Loka (atmosphere), Svar Loka (heaven of Indra)
- Mahar Loka, Jana Loka, Tapo Loka, Satya Loka (Brahma's world)
- Beyond these is the imperishable realm (Vaikuntha / Kailasha)

The Lower Worlds:
- Atala, Vitala, Sutala, Talatala, Mahatala, Rasatala, Patala
- Seven lower regions, each with its own beings and characteristics

The Symbolic Meaning:
- The cosmos is a manifestation of the divine
- Time is cyclical, not linear — creation and dissolution alternate eternally
- Every being is part of a vast cosmic order
- The physical universe is just one layer of a multi-dimensional reality""",
        domain="puranas",
        category="cosmology",
        tags=["cosmology", "yugas", "kalpa", "manvantara", "creation", "cycles", "lokas"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "Kali Yuga: We are currently approximately 5,000 years into Kali Yuga, which will last 432,000 years — an age of decline, conflict, and materialism",
            "The day of Brahma: When Brahma wakes, the universe manifests; when he sleeps, it dissolves — this cycle repeats for 100 divine years",
            "The fish avatar (Matsya): At the end of a Kalpa, Vishnu takes the form of a fish to save Manu (the progenitor of humanity) and the seven sages from the great flood",
            "The churning of the ocean (Samudra Manthan): Devas and Asuras churn the cosmic ocean to obtain Amrita (nectar of immortality) — a story of creation through cooperation and conflict",
        ],
        references=[
            "The Puranic timescales are remarkably close to modern cosmological estimates of the age of the universe",
            "Carl Sagan noted: 'The Hindu religion is the only one of the world's great faiths dedicated to the idea that the Cosmos itself undergoes an immense, indeed an infinite, number of deaths and rebirths'",
            "The concept of cyclical time influenced the Mayan calendar and other ancient civilizations",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="puranas-bhagavata-001",
        title="Bhagavata Purana — The Crown Jewel of Puranic Literature",
        content="""The Bhagavata Purana (also known as Srimad Bhagavatam) is the most celebrated and influential of all the Puranas. Composed in Sanskrit with a poetic style of extraordinary beauty, it presents the philosophy of bhakti (devotion) at its highest expression.

Structure:
- 12 Skandhas (books), 335 chapters, approximately 18,000 verses
- The 10th Skandha (about Krishna) is the longest and most beloved
- Attributed to Vyasa, who is said to have composed it after the Mahabharata

Key Narratives:

The Story of Krishna (Book 10):
- Birth in Mathura, smuggled across the Yamuna to Gokul
- Childhood pranks (stealing butter, lifting Govardhan hill)
- Rasa Lila with the Gopis — the divine dance of love
- Slaying demons (Putana, Kamsa, Aghasura)
- The flute that enchants all creation

The Story of Prahlada (Book 7):
- The young devotee of Vishnu, born to the demon king Hiranyakashipu
- His father tries to kill him repeatedly — thrown from cliffs, trampled by elephants, poisoned
- Vishnu appears as Narasimha (half-man, half-lion) at dusk (neither day nor night), on the threshold (neither inside nor outside), on his lap (neither earth nor sky), and slays the demon with his claws (neither weapon nor hand)
- Teaches that devotion transcends all worldly power

The Story of Dhruva (Book 4):
- A 5-year-old prince denied his father's lap, goes to the forest to find Vishnu
- Performs severe tapasya, stands on one foot, eventually becomes the Pole Star (Dhruva Nakshatra)
- Teaches the power of determination and devotion

The Gopi Geeta and other teachings:
- The Gopis' separation from Krishna — the highest form of longing for God
- Uddhava Gita (Book 11): Krishna's final teachings to his cousin Uddhava before leaving the world

Core Philosophy:
- Bhakti as the highest spiritual practice — superior to jnana (knowledge) and karma (action)
- The personal God (Bhagavan) is the supreme reality
- Love for God is the natural state of the soul
- The divine plays (lila) to attract souls back to itself
- Surrender (prapatti) is the simplest path to liberation""",
        domain="puranas",
        category="mahapuranas",
        tags=["bhagavata", "krishna", "bhakti", "prahlada", "dhruva", "gopis", "narasimha"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "Krishna and the Gopis: The Gopis abandon everything — husbands, children, society — to dance with Krishna. This represents the soul abandoning all attachments for union with the divine",
            "Narasimha avatar: Appears at twilight (neither day nor night), on a threshold (neither inside nor outside), on his lap (neither earth nor sky), with claws (neither weapon nor hand) — showing that God transcends all categories",
            "The butter thief: Krishna steals butter from the Gopis' homes — symbolizing God stealing the hearts of his devotees, and also the removal of the 'butter' of ego that covers the soul",
            "Prahlada's fearlessness: 'I do not fear death, for Vishnu is within me. Where can I go that is not already filled with God?'",
        ],
        references=[
            "The Bhagavata Purana is considered the 'ripe fruit of the wish-fulfilling tree of the Vedas'",
            "It has inspired countless commentaries, the most famous being by Sridhara Swami and Jiva Goswami",
            "The Bhakti movement across India (Mirabai, Tulsidas, Chaitanya, Tukaram) draws heavily from the Bhagavata",
        ],
    ))

    return domain
