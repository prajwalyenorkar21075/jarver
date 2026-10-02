"""Itihasa — Ramayana and Mahabharata."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_itihasa_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="itihasa",
        description="The two great Indian epics — Ramayana and Mahabharata. Itihasa means 'thus indeed it happened' — sacred histories that teach dharma through narrative.",
        subcategories=["ramayana", "mahabharata", "dharma", "characters", "teachings"],
        metadata={"tradition": "Hindu", "language": "Sanskrit", "genre": "Epic (Itihasa)"},
    )

    domain.add_entry(KnowledgeEntry(
        id="itihasa-ramayana-001",
        title="Ramayana — The Epic of Dharma and Devotion",
        content="""The Ramayana, composed by the sage Valmiki, is one of the two great Indian epics. It tells the story of Rama, the ideal king and avatar of Vishnu, and his quest to rescue his wife Sita from the demon king Ravana.

Structure:
- Approximately 24,000 verses (shlokas) organized into 7 Kandas (books)
- Composed in Anushtubh meter (shloka)
- Written in Sanskrit, c. 5th-4th century BCE (traditional dating)

The Seven Kandas:
1. Bala Kanda (Book of Youth): Birth of Rama and his brothers, Vishvamitra's protection, Sita's swayamvara
2. Ayodhya Kanda (Book of Ayodhya): Dasharatha's decision, Kaikeyi's boons, Rama's exile, Dasharatha's death
3. Aranya Kanda (Book of the Forest): Life in the forest, Surpanakha's disfigurement, the golden deer, Sita's abduction
4. Kishkindha Kanda (Book of Kishkindha): Alliance with Sugriva, death of Vali, search for Sita, Hanuman's leap to Lanka
5. Sundara Kanda (Book of Beauty): Hanuman's exploits in Lanka, finding Sita in Ashoka Vatika, burning Lanka
6. Yuddha Kanda (Book of War): The great battle, Rama's victory, Ravana's death, Sita's trial by fire, return to Ayodhya
7. Uttara Kanda (Book of Aftermath): Rama's reign (Rama Rajya), Sita's banishment, Lava and Kusha, Sita's return to Earth, Rama's ascent to heaven

Core Themes:
- Dharma: Righteous conduct in every relationship — as son, brother, husband, king
- Ideal relationships: Rama as ideal king, Sita as ideal wife, Lakshmana as ideal brother, Hanuman as ideal devotee
- The triumph of dharma over adharma (righteousness over evil)
- The power of devotion and surrender to God
- The consequences of desire and attachment
- The importance of truth and keeping one's word (Rama honoring his father's promise)""",
        domain="itihasa",
        category="ramayana",
        tags=["ramayana", "valmiki", "rama", "sita", "hanuman", "ravana", "epic", "dharma"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "Rama's acceptance of exile: 'The word of a father must be kept, even at the cost of one's life and kingdom' — demonstrates the supreme importance of truth",
            "Hanuman's devotion: 'I am Rama's servant' — Hanuman tears open his chest to show Rama and Sita dwelling in his heart",
            "Shabari's berries: The elderly devotee Shabari offers half-eaten berries to Rama — he accepts them with love, valuing devotion over formality",
            "Rama Rajya: Rama's ideal kingdom where all subjects are happy, just, and prosperous — the model of righteous governance",
        ],
        references=[
            "Valmiki is called the Adi Kavi (First Poet) — he is said to have invented the shloka meter",
            "The Ramayana has many versions: Tulsidas's Ramcharitmanas (Hindi), Kamban's Ramavataram (Tamil), and others",
            "The Ramayana's influence extends across Southeast Asia — Thailand's Ramakien, Indonesia's Kakawin Ramayana",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="itihasa-ramayana-002",
        title="Key Characters of the Ramayana",
        content="""The Ramayana's characters embody ideal qualities and teach through their actions the principles of dharma.

Rama (राम):
- The seventh avatar of Vishnu, born as prince of Ayodhya
- Embodies maryada purushottama — the perfect man of honor and principle
- Qualities: Truthful, courageous, compassionate, just, self-controlled
- His life teaches: Keeping one's word, respecting elders, protecting the weak, ruling with dharma

Sita (सीता):
- Daughter of King Janaka, found in a furrow of the earth (Sita = furrow)
- Embodies pativrata dharma — the ideal wife devoted to her husband
- Qualities: Virtuous, courageous, patient, steadfast, compassionate
- Her life teaches: Loyalty, inner strength, dignity in suffering, devotion

Lakshmana (लक्ष्मण):
- Rama's younger brother, an incarnation of Shesha (the serpent)
- Embodies fraternal devotion — accompanies Rama into exile for 14 years
- Qualities: Loyal, fierce, protective, selfless
- His life teaches: Brotherhood, service, sacrifice for loved ones

Hanuman (हनुमान):
- The vanara (monkey) warrior, son of Vayu (wind god) and Anjana
- Embodies bhakti (devotion) and selfless service
- Qualities: Immensely strong, supremely intelligent, completely humble, devoted to Rama
- His life teaches: The power of devotion, overcoming ego, serving God in all beings
- Known as the "son of the wind god," he can leap across oceans, change his size, and carry mountains

Ravana (रावण):
- The demon king of Lanka, a great scholar and devotee of Shiva
- Embodies the tragedy of knowledge without wisdom, power without righteousness
- Ten heads represent: The five senses and five organs of action — all under the control of desire
- His downfall: Abducting Sita out of desire, refusing to listen to wise counsel
- Despite being the villain, he is also a complex character — a great king and scholar overcome by ego

Other Important Characters:
- Dasharatha: Rama's father, king of Ayodhya, bound by his word
- Kaikeyi: The queen whose boons send Rama into exile
- Bharata: Rama's brother who rules as regent, placing Rama's sandals on the throne
- Jatayu: The noble eagle who dies fighting Ravana to protect Sita
- Vibhishana: Ravana's righteous brother who joins Rama's side""",
        domain="itihasa",
        category="ramayana",
        tags=["characters", "rama", "sita", "hanuman", "ravana", "lakshmana", "bharata"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "Bharata's devotion: When Rama is exiled, Bharata refuses the throne, places Rama's sandals on it, and rules as a servant for 14 years",
            "Jatayu's sacrifice: The old eagle fights Ravana alone to save Sita, dying from his wounds — Rama performs his last rites as a father would for a son",
            "Vibhishana's righteousness: Despite being Ravana's brother, he advises dharma. When Ravana rejects him, he joins Rama — showing that dharma transcends loyalty to evil",
            "Hanuman's humility: Despite his immense powers, Hanuman says 'I can do nothing without Rama's grace'",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="itihasa-mahabharata-001",
        title="Mahabharata — The Great Epic of Dharma and Human Complexity",
        content="""The Mahabharata, attributed to the sage Vyasa (Veda Vyasa), is the longest epic poem in the world — a vast encyclopedia of Indian philosophy, ethics, politics, and spirituality. Its name means "The Great Tale of the Bharata Dynasty."

Structure:
- Approximately 100,000 shlokas (couplets) — about 1.8 million words
- 18 Parvas (books), plus the Harivamsha as a supplement
- Contains within it the Bhagavad Gita (Chapters 23-40 of Book 6)
- The longest poem ever written — 10 times longer than the Iliad and Odyssey combined

The 18 Parvas:
1. Adi Parva: Ancestry, birth of Pandavas and Kauravas, the house of lac
2. Sabha Parva: The gambling match, Draupadi's disrobing, the exile
3. Vana Parva: The 12 years of forest exile
4. Virata Parva: The 13th year in disguise at King Virata's court
5. Udyoga Parva: Peace missions fail, war preparations
6. Bhishma Parva: The Bhagavad Gita and first 10 days of war (Bhishma's fall)
7. Drona Parva: Days 11-15 of war (Drona's command and fall)
8. Karna Parva: Karna's command and fall (days 16-17)
9. Shalya Parva: Final days of war, Duryodhana's fall
10. Sauptika Parva: Ashvatthama's night massacre
11. Stri Parva: The women lament the dead
12. Shanti Parva: Bhishma's teachings on dharma and governance to Yudhishthira
13. Anushasana Parva: Bhishma's final teachings on gifts and duties
14. Ashvamedhika Parva: Yudhishthira's horse sacrifice
15. Ashramavasika Parva: Dhritarashtra and Gandhari retire to the forest
16. Mausala Parva: The destruction of the Yadava clan
17. Mahaprasthanika Parva: The Pandavas' final journey to heaven
18. Svargarohana Parva: The Pandavas in heaven

Core Theme: Dharma in its complexity — the Mahabharata does not present simple moral lessons but explores the gray areas where duty conflicts with duty, where right action has wrong consequences, and where the path of righteousness is not clear.""",
        domain="itihasa",
        category="mahabharata",
        tags=["mahabharata", "vyasa", "pandavas", "kauravas", "kurukshetra", "epic", "dharma"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "The central conflict: 100 Kaurava brothers vs. 5 Pandava brothers — a war of succession that becomes a war of dharma",
            "Yudhishthira's dilemma: As king, he must govern justly; as a Kshatriya, he must fight; as a brother, he must protect — but all paths lead to war",
            "The war lasts 18 days and nearly destroys the entire Kuru dynasty — a meditation on the cost of adharma",
            "Bhishma lies on a bed of arrows for 58 nights, teaching dharma to Yudhishthira — the longest deathbed discourse in literature",
        ],
        references=[
            "Vyasa is both the author and a character in the Mahabharata — he is the grandfather of both Pandavas and Kauravas",
            "The Mahabharata says of itself: 'What is found here, may be found elsewhere; what is not here, is nowhere'",
            "Ganesha is said to have written the Mahabharata as Vyasa dictated it — on condition that Vyasa never pause",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="itihasa-mahabharata-002",
        title="The Pandavas and Kauravas — Key Characters of the Mahabharata",
        content="""The Mahabharata's characters are deeply human — flawed, complex, and morally ambiguous. They teach through both their virtues and their failures.

The Five Pandavas (sons of Pandu, born through divine boons to Kunti and Madri):

Yudhishthira (युधिष्ठिर):
- Eldest, son of Dharma (righteousness)
- Embodies dharma but is also bound by his word — his gambling addiction leads to disaster
- The just king who must wage an unjust war
- Known as "Dharmaraja" — the king of righteousness

Bhima (भीम):
- Second, son of Vayu (wind god)
- Embodies physical strength and fierce loyalty
- Vows to kill all 100 Kauravas and fulfills his oath
- His rage at Draupadi's humiliation drives the war

Arjuna (अर्जुन):
- Third, son of Indra (king of gods)
- The greatest warrior, but conflicted about fighting his own kin
- The recipient of the Bhagavad Gita's teachings
- Represents the soul's journey from confusion to clarity

Nakula (नकुल) and Sahadeva (सहदेव):
- Twins, sons of the Ashwini twins (divine physicians)
- Nakula: Handsome, skilled with swords
- Sahadeva: Wise, expert in astronomy and administration
- The least prominent but embody loyalty and knowledge

Draupadi (द्रौपदी):
- Wife of all five Pandavas (born from fire during a yajna)
- The catalyst of the war — her humiliation in the Kaurava court
- Embodies shakti (divine feminine power), dignity, and righteous anger
- Her vow to tie her hair only after washing it with Dushasana's blood is fulfilled

The Kauravas (100 sons of Dhritarashtra and Gandhari):
Duryodhana (दुर्योधन):
- Eldest Kaurava, the primary antagonist
- Embodies envy, pride, and the refusal to share power
- A complex villain — also a loyal friend (to Karna) and a brave warrior
- His famous words: "I would rather go to hell than give up even a needlepoint of land"

Dushasana (दुःशासन):
- Second Kaurava, who drags Draupadi into the assembly and attempts to disrobe her
- His act is the moral tipping point that makes war inevitable

Karna (कर्ण):
- The tragic hero — actually the eldest Pandava (born to Kunti before marriage), abandoned and raised by a charioteer
- Embodies generosity, loyalty, and the tragedy of unknown identity
- Fights for Duryodhana out of loyalty, knowing he is on the wrong side
- His gift (daan) — giving away his divine armor — leads to his death

Other Key Characters:
- Bhishma: The grandsire who vows celibacy, bound by his oath to serve the throne even when it is occupied by adharma
- Drona: The teacher who trains both sides, then fights against the Pandavas
- Krishna: The divine guide, charioteer of Arjuna, delivers the Bhagavad Gita
- Shakuni: The cunning uncle who orchestrates the gambling match""",
        domain="itihasa",
        category="mahabharata",
        tags=["pandavas", "kauravas", "yudhishthira", "arjuna", "bhima", "draupadi", "karna", "krishna"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "Karna's tragedy: He gives away his divine kavacha (armor) to Indra in disguise, knowing it will lead to his death — but he cannot refuse a request, such is his generosity",
            "Bhishma's dilemma: He loves the Pandavas but is bound by oath to protect the throne of Hastinapura, even when Duryodhana occupies it unjustly",
            "Draupadi's question: After being gambled away, she asks the assembly 'Did Yudhishthira lose himself first, or did he lose me first?' — no one can answer, exposing the moral ambiguity",
            "Krishna's counsel: He does not tell Arjuna what to do but helps him see clearly — the Gita is about enlightened action, not blind obedience",
        ],
    ))

    return domain
