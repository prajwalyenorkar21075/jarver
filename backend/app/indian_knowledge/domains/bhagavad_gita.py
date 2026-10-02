"""Bhagavad Gita — Philosophical Dialogue from the Mahabharata."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_bhagavad_gita_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="bhagavad_gita",
        description="The Bhagavad Gita — the 700-verse philosophical dialogue between Krishna and Arjuna on the battlefield of Kurukshetra. A comprehensive guide to life, duty, and spiritual liberation.",
        subcategories=["karma_yoga", "jnana_yoga", "bhakti_yoga", "dharma", "chapters"],
        metadata={"tradition": "Hindu", "language": "Sanskrit", "location": "Mahabharata Book 6 (Bhishma Parva), Chapters 23-40"},
    )

    domain.add_entry(KnowledgeEntry(
        id="gita-overview-001",
        title="Bhagavad Gita — Context and Structure",
        content="""The Bhagavad Gita (भगवद्गीता, "Song of the Lord") is a 700-verse dialogue between Prince Arjuna and his charioteer Lord Krishna, set on the battlefield of Kurukshetra just before the great war of the Mahabharata.

The Setting:
- Arjuna's chariot is positioned between the two armies
- He sees his teachers, elders, cousins, and friends on the opposing side
- Overcome with grief and moral confusion, he refuses to fight
- Krishna, who is the Supreme Being (Bhagavan) incarnate, teaches him the nature of reality, duty, and the path to liberation

The Structure (18 Chapters, grouped into three sextads):

Chapters 1-6: Karma Yoga (The Path of Action)
- Chapter 1: Arjuna's Grief — the crisis of duty
- Chapter 2: Sankhya Yoga — the immortal nature of the Self; introduction to karma yoga
- Chapter 3: Karma Yoga — selfless action without attachment to results
- Chapter 4: Jnana-Karma-Sannyasa Yoga — knowledge and the science of action
- Chapter 5: Karma-Sannyasa Yoga — renunciation of action vs. renunciation of fruits
- Chapter 6: Dhyana Yoga — meditation and self-control

Chapters 7-12: Jnana Yoga and Bhakti Yoga (Knowledge and Devotion)
- Chapter 7: Jnana-Vijnana Yoga — knowledge of the Absolute and the relative
- Chapter 8: Aksara-Brahma Yoga — the imperishable Brahman and the path at death
- Chapter 9: Raja-Vidya-Raja-Guhya Yoga — the royal knowledge and royal secret
- Chapter 10: Vibhuti Yoga — divine manifestations and glories
- Chapter 11: Visvarupa-Darsana Yoga — the universal form revealed
- Chapter 12: Bhakti Yoga — the path of devotion

Chapters 13-18: Understanding Prakriti and Purusha (Matter and Spirit)
- Chapter 13: Ksetra-Ksetrajna Vibhaga Yoga — the field and the knower of the field
- Chapter 14: Gunatraya-Vibhaga Yoga — the three gunas (sattva, rajas, tamas)
- Chapter 15: Purushottama Yoga — the supreme person beyond the perishable and imperishable
- Chapter 16: Daivasura-Sampad-Vibhaga Yoga — divine and demonic natures
- Chapter 17: Sraddhatraya-Vibhaga Yoga — the three kinds of faith
- Chapter 18: Moksa-Sannyasa Yoga — liberation through renunciation; the final teaching

The Gita synthesizes the three main paths of Hindu spirituality: Karma Yoga (selfless action), Jnana Yoga (knowledge), and Bhakti Yoga (devotion).""",
        domain="bhagavad_gita",
        category="chapters",
        tags=["gita", "krishna", "arjuna", "kurukshetra", "18 chapters", "overview"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "The central dilemma: Arjuna must fight a war against his own kin — is it right to kill for justice, or should he renounce violence? Krishna's answer transcends both options",
            "Krishna reveals his Vishvarupa (Universal Form) in Chapter 11 — Arjuna sees all the universe, all beings, all time, contained within Krishna's body",
            "The Gita begins with Dhritarashtra's question: 'What did my sons and the sons of Pandu do when they assembled on the battlefield?' — showing that the war was sealed by fate",
            "Arjuna's first words of surrender: 'I am your disciple. Teach me, for I am confused about my duty' (2.7) — the student ready to learn",
        ],
        references=[
            "The Gita is called 'Gitopanishad' — the Upanishad of the Gita, the essence of all Vedic wisdom",
            "Mahatma Gandhi called it his 'spiritual dictionary' and interpreted it as an allegory for the inner battle between good and evil",
            "Commentaries by Shankara (Advaita), Ramanuja (Vishishtadvaita), and Madhva (Dvaita) represent the three major philosophical schools",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="gita-karma-001",
        title="Karma Yoga — The Path of Selfless Action",
        content="""Karma Yoga is the Gita's central teaching — the path of performing one's duty without attachment to the results. It resolves Arjuna's dilemma by showing that action itself is not the problem; attachment is.

The Core Teaching:
"Karmanye vadhikaraste Ma Phaleshu Kadachana"
"You have the right to perform your duty, but not to the fruits of action" (2.47)

This does NOT mean: Don't care about results.
It DOES mean: Do your best, then let go of attachment to success or failure.

Key Principles:

1. Nishkama Karma (Desireless Action):
   - Act without selfish motivation
   - Offer all actions to the divine
   - The fruits belong to the cosmic order, not to you
   - "Yoga is skill in action" (Yogah karmasu kausalam, 2.50)

2. Svadharma (One's Own Duty):
   - Each person has a duty according to their nature and position
   - "Better to perform one's own duty imperfectly than to perform another's duty perfectly" (18.47)
   - Arjuna's svadharma as a Kshatriya (warrior) is to fight for justice
   - Running from one's duty creates more karma, not less

3. The Self is Not the Doer:
   - "The Self is not the doer" — actions are performed by the gunas (qualities of nature)
   - The wise person acts as an instrument of the divine
   - Identification with the ego ("I am the doer") creates bondage
   - Liberation comes from seeing the Self as the eternal witness

4. Equanimity (Samattvam):
   - "Yoga is evenness" (Samatvam yoga uchyate, 2.48)
   - Remain balanced in success and failure, pleasure and pain, victory and defeat
   - This equanimity is the mark of the sthitaprajna (person of steady wisdom)

5. Yajna (Sacrifice):
   - All action should be performed as a sacrifice to the divine
   - "The universe is born from action; action arises from Brahman" (3.15)
   - Even eating, breathing, and sleeping can be offerings when done with awareness

The Stithaprajna (Person of Steady Wisdom, Chapter 2):
- Unshaken by adversity, not elated by prosperity
- Free from attachment, fear, and anger
- Sees the same Self in all beings
- Has withdrawn the senses from sense objects "as a tortoise withdraws its limbs" (2.58)""",
        domain="bhagavad_gita",
        category="karma_yoga",
        tags=["karma yoga", "nishkama karma", "svadharma", "selfless action", "equanimity", "duty"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "A doctor treats patients without attachment to whether they recover — she does her best, then lets go. This is karma yoga in daily life",
            "Arjuna fights not for personal glory or hatred of the Kauravas, but as an offering to dharma — his duty as a warrior for justice",
            "Krishna says: 'I have nothing to gain in the three worlds, yet I engage in action' (3.22) — even God acts without attachment, as an example for humanity",
            "The lotus leaf in water: 'Like a lotus leaf untouched by water, one who acts offering everything to Brahman is untouched by sin' (5.10)",
        ],
        references=[
            "Karma Yoga is sometimes called 'the yoga of action' or 'the yoga of selfless service'",
            "Mahatma Gandhi's entire philosophy of public service was based on karma yoga",
            "The teaching does not advocate inaction — it advocates action without the bondage of desire",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="gita-jnana-001",
        title="Jnana Yoga — The Path of Knowledge and Wisdom",
        content="""Jnana Yoga is the path of knowledge — the intellectual and intuitive understanding of the nature of reality, the Self, and the relationship between the two. It is considered the most direct but also the most difficult path.

Core Teachings:

1. Atman and Brahman (The Self and the Absolute):
   - "The Self (Atman) in all beings, and all beings in the Self" (6.29)
   - The individual Self is eternal, indestructible, unchangeable
   - "Weapons cannot cut it, fire cannot burn it, water cannot wet it, wind cannot dry it" (2.23)
   - Brahman is the ultimate reality — the ground of all existence
   - The goal is to realize the identity of Atman and Brahman

2. The Three Levels of Reality:
   - Adhibhuta: The physical, material world (elements, bodies, objects)
   - Adhidaiva: The divine, cosmic level (gods, celestial forces)
   - Adhyatma: The spiritual, inner level (the Self, consciousness)
   - The wise see the unity underlying all three

3. The Gunas (Qualities of Nature):
   - Sattva: Purity, light, knowledge, harmony — binds the soul to happiness
   - Rajas: Passion, activity, desire — binds the soul to action
   - Tamas: Ignorance, inertia, darkness — binds the soul to heedlessness
   - All of nature (Prakriti) is composed of these three gunas
   - The goal is to transcend all three gunas (trigunatita)
   - "When the seer sees no agent other than the gunas, and knows that which is beyond the gunas, they attain to My being" (14.19)

4. Maya and Avidya (Illusion and Ignorance):
   - The phenomenal world is veiled by Maya — the power that makes the one appear as many
   - Avidya (ignorance) is the root cause of suffering — mistaking the temporary for the eternal
   - "Deluded by the three gunas, the world does not know Me, the imperishable, beyond the gunas" (7.13)
   - Knowledge (jnana) destroys this ignorance like fire burns wood

5. The Knower of Brahman:
   - "One who knows Brahman attains the Supreme" (8.16)
   - Not intellectual knowledge but direct realization (anubhava)
   - The jivanmukta: liberated while still living
   - "Having known this, you will not fall again into delusion" (4.35)

The Metaphor of the Chariot (from Katha Upanishad, echoed in Gita):
- The body is the chariot
- The senses are the horses
- The mind is the reins
- The intellect (buddhi) is the charioteer
- The Self (Atman) is the rider
- When the intellect controls the mind, and the mind controls the senses, the chariot reaches its destination""",
        domain="bhagavad_gita",
        category="jnana_yoga",
        tags=["jnana yoga", "atman", "brahman", "gunas", "maya", "knowledge", "wisdom"],
        difficulty=DifficultyLevel.ADVANCED,
        examples=[
            "The gold and ornaments: All gold ornaments are essentially gold — different names and forms, but one substance. Similarly, all beings are manifestations of Brahman",
            "The space in pots: Space inside a pot seems limited, but when the pot breaks, the space is revealed as the same unlimited space everywhere. The Self appears limited by the body but is actually infinite",
            "Krishna says: 'As the same fire enters the world and assumes forms according to what it enters, so does the one Self within all beings' (7.10)",
            "The two birds (Mundaka Upanishad): Two birds on the same tree — one eats the fruit (experiencing the world), the other watches (the witness Self). The first bird is the jiva, the second is Ishvara",
        ],
        references=[
            "Jnana Yoga is considered the most direct path but requires the greatest intellectual and spiritual capacity",
            "Adi Shankara's commentary on the Gita emphasizes jnana as the primary means of liberation",
            "The Gita synthesizes jnana with karma and bhakti — knowledge must be lived, not just understood",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="gita-bhakti-001",
        title="Bhakti Yoga — The Path of Devotion and Love",
        content="""Bhakti Yoga is the path of love and devotion to God — considered the easiest and most accessible path, open to all regardless of caste, gender, or intellectual capacity. Krishna declares it the highest of all paths.

Core Teachings:

1. Supreme Devotion:
   - "To those who are constantly devoted and worship Me with love, I give the yoga of understanding by which they come to Me" (10.10)
   - God is not distant or abstract — He is a person to be loved
   - The relationship can be as parent-child, master-servant, friend-friend, or beloved-beloved
   - "Those who worship Me with devotion, in Me they exist, and I in them" (9.29) (Note: this is a paraphrase — the actual verse 9.29 is about equanimity; the sentiment is expressed in various verses)

2. Surrender (Prapatti):
   - "Abandon all dharmas and take refuge in Me alone" (18.66)
   - This is the Gita's most famous and decisive verse — the ultimate teaching
   - Complete surrender to God's will, trusting that the divine will guide and protect
   - Not passive resignation but active trust — doing one's duty while surrendering the results

3. The Devotee's Qualities (Chapter 12):
   - "Those who follow this immortal path of devotion with faith, regarding Me as the supreme goal — they are the most perfect in yoga" (12.2)
   - The ideal devotee: Free from hatred, friendly and compassionate, without ego, equal in pleasure and pain, forgiving, content, self-controlled, firm in resolve
   - "He who neither rejoices nor grieves, neither fears nor desires — such a devotee is dear to Me" (12.16-17)

4. Seeing God in All:
   - "He who sees Me everywhere and sees everything in Me — I am not lost to him, and he is not lost to Me" (6.30)
   - All beings are manifestations of the divine
   - Service to others is service to God
   - "The wise see with equal vision a learned brahmin, a cow, an elephant, a dog, and an outcaste" (5.18)

5. The Power of the Name and Remembrance:
   - "Whatever a person remembers at the time of death, that they attain" (8.6)
   - Therefore, remember God always — through chanting, prayer, and mindfulness
   - "Fix your mind on Me, be devoted to Me, sacrifice to Me, bow down to Me — thus you shall certainly reach Me" (18.65)
   - The simple repetition of God's name (japa) purifies the heart

6. Krishna's Universal Form (Chapter 11):
   - Arjuna is granted divine sight and sees Krishna's Vishvarupa
   - He sees all the gods, all beings, all time — past, present, future — within Krishna
   - He sees the Kaurava warriors rushing into Krishna's mouths "like moths into a flame"
   - Terrified and awed, Arjuna begs Krishna to return to his gentle human form
   - This vision reveals that God is both the terrible and the gentle, the creator and the destroyer

The Nine Forms of Bhakti (Navavidha Bhakti, from Bhagavata Purana):
1. Shravana — Hearing about God
2. Kirtana — Singing God's glories
3. Smarana — Remembering God
4. Padasevana — Serving God's feet
5. Archana — Worshiping God
6. Vandana — Bowing to God
7. Dasya — Serving God as a servant
8. Sakhya — Befriending God
9. Atmanivedana — Surrendering the self completely""",
        domain="bhagavad_gita",
        category="bhakti_yoga",
        tags=["bhakti yoga", "devotion", "surrender", "krishna", "love", "prapatti", "vishvarupa"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "Krishna says: 'Even if the most sinful worships Me with undivided devotion, they must be regarded as righteous, for they have rightly resolved' (9.30)",
            "The Gopis of Vrindavan: Their love for Krishna was so pure that they forgot social conventions, family duties, everything — only Krishna existed for them. This is the highest bhakti",
            "Hanuman tearing his chest: To show that Rama and Sita dwell in his heart — the devotee's heart is God's dwelling place",
            "Arjuna after the Vishvarupa: 'I bow to You with reverence. As a father to a son, as a friend to a friend, as a lover to a beloved — please bear with me, forgive my casualness' (11.42)",
        ],
        references=[
            "Bhakti Yoga is considered the easiest path because it requires no special intellectual capacity or physical austerity — only love",
            "The Bhakti movement (6th-18th centuries) spread the Gita's message of loving devotion across all of India",
            "Ramakrishna Paramahamsa taught that bhakti is the path most suited for the current age (Kali Yuga)",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="gita-dharma-001",
        title="Dharma in the Gita — Duty, Righteousness, and the Moral Order",
        content="""The Gita is set against the backdrop of a moral crisis — Arjuna's duty as a warrior conflicts with his compassion for his kinsmen. Krishna's teaching resolves this by presenting a comprehensive vision of dharma.

Key Aspects of Dharma in the Gita:

1. Svadharma (One's Own Duty):
   - "It is better to perform one's own duty, even if imperfectly, than to perform another's duty perfectly" (18.47)
   - Each person has a duty based on their nature (svabhava) and position in society
   - Arjuna's svadharma as a Kshatriya is to fight for justice — running from it would be adharma
   - "Better is one's own dharma, though imperfectly performed; the dharma of another, though well performed, is a source of fear" (3.35)

2. The Cosmic Order (Rita/Dharma):
   - Dharma is not just social duty — it is the cosmic order that sustains the universe
   - "From dharma arises the cosmic order; the universe runs on dharma" (paraphrase of 3.15-16)
   - When dharma declines, God incarnates to restore it (4.7-8):
     "Whenever dharma declines and adharma rises, I manifest Myself. For the protection of the good, for the destruction of the wicked, and for the establishment of dharma, I am born in every age"
   - The war of Kurukshetra is itself an act of restoring dharma

3. Dharma vs. Adharma:
   - Dharma: That which upholds, sustains, and leads to the welfare of all
   - Adharma: That which destroys, divides, and leads to suffering
   - The Kauravas represent adharma — greed, injustice, cruelty
   - The Pandavas represent dharma — but even they are not perfect
   - Dharma is subtle (sukshma) — it requires discrimination (viveka)

4. The Paradox of Dharma:
   - Sometimes dharma requires actions that seem immoral from a conventional standpoint
   - Arjuna must kill his teachers and elders — but they are on the side of adharma
   - Krishna uses the metaphor of the body: Just as a surgeon cuts the body to heal it, the warrior fights to restore cosmic order
   - The key is the motivation: Is the action for selfish gain, or for the welfare of all?

5. Dharma and Liberation:
   - Performing one's dharma selflessly leads to purification of the heart
   - A purified heart is ready for self-knowledge
   - Self-knowledge leads to liberation (moksha)
   - Thus, dharma is not an end in itself but a means to the ultimate goal
   - "Having performed action for the sake of sacrifice, the sages attain the supreme peace" (4.30)

The Gita's Resolution:
Krishna does not tell Arjuna to abandon the war (that would be abandoning his dharma). Instead, he teaches him to fight without hatred, without desire for the kingdom, as an offering to the divine. This transforms a seemingly violent act into an act of dharma and devotion.""",
        domain="bhagavad_gita",
        category="dharma",
        tags=["dharma", "svadharma", "righteousness", "duty", "cosmic order", "kurukshetra", "adharma"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "Krishna's avatar declaration (4.7-8): 'Whenever dharma declines, I manifest Myself' — God incarnates not to reward the good but to restore cosmic balance",
            "The paradox of righteous war: Arjuna's teachers (Drona, Bhishma) are virtuous men, but they support adharma by fighting for Duryodhana. Their virtue does not excuse their complicity",
            "Dhritarashtra's blindness: The king's physical blindness symbolizes his moral blindness — he cannot see the adharma of his sons because of his attachment to them",
            "Yudhishthira's truth: Even the most righteous king must tell a half-truth about Ashvatthama's death to win the war — showing that dharma is complex and contextual",
        ],
        references=[
            "The Gita's teaching on dharma has been compared to Kant's categorical imperative — duty for duty's sake",
            "Gandhi interpreted the war allegorically — the battlefield is the human soul, and the war is the eternal struggle between higher and lower nature",
            "The Gita does not advocate violence — it acknowledges that in a fallen world, sometimes force is necessary to protect dharma, but it must be done without hatred or desire",
        ],
    ))

    return domain
