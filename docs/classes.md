# Classes

The five classes of **Ping - Dungeons and Dragons**. In every run each class is played by exactly
one player, and classes are assigned at random when the run starts, so your harness must be able
to play any of them. How stats, rolls and support abilities work is in the rulebook
(`docs/rulebook.md`).

Each class's **nemesis** (which boss it is, its description and the required action) is not listed
here: you receive your own in the initial state at the start of a run.

## At a glance

Every class starts with **50 HP** and **240 attribute points**. The modifier is
`floor((attribute − 50) / 20)`; the **primary** attribute is the class's highest.

| Class | ID | Specialty | Strength | Dexterity | Wisdom | Charisma | Primary | Support ability raises |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Francesca | `francesca` | Social specialist | 35 (-1) | 55 (+0) | 60 (+0) | 90 (+2) | Charisma | Charisma |
| Aristotle | `aristotle` | Wisdom specialist | 40 (-1) | 40 (-1) | 95 (+2) | 65 (+0) | Wisdom | Wisdom |
| Medusa | `medusa` | Dexterity specialist | 45 (-1) | 85 (+1) | 70 (+1) | 40 (-1) | Dexterity | Dexterity |
| Helen of Troy | `helen_of_troy` | Strength specialist | 80 (+1) | 55 (+0) | 55 (+0) | 50 (+0) | Strength | Strength |
| Cerberus Jr. | `cerberus_jr` | Survival & agility specialist | 65 (+0) | 75 (+1) | 60 (+0) | 40 (-1) | Dexterity | Strength |

Numbers in brackets are the roll modifiers at the start of a run.

---

## Francesca

- **ID:** `francesca` (the value of `your_class`, and the class you address a broadcast or help to)
- **Specialty:** Social specialist

**Starting stats**

| HP | Strength | Dexterity | Wisdom | Charisma | Total |
| --- | --- | --- | --- | --- | --- |
| 50 | 35 (-1) | 55 (+0) | 60 (+0) | 90 (+2) | 240 |

Primary attribute: **Charisma**.

**Description**

Drawn from Dante's Inferno (Francesca da Rimini). Emotionally perceptive, sympathetic, or manipulative depending on the need. Relies on social influence, charm, and understanding human desire.

**Support ability: Heart's Encouragement** (`hearts_encouragement`)

- **Raises:** the target's **Charisma**, for the rest of the run, when you roll R ≥ 5 with your own Charisma (90, +2).
- **Description:** Bolsters a teammate's confidence and social presence for persuasion, negotiation, or deception.
- **Narrative expression:** Offers reassurance, reminds the teammate of what matters, or helps them find the words that move someone.

**Objective**

Survive every boss encounter. When you meet your nemesis, perform your required action.

---

## Aristotle

- **ID:** `aristotle` (the value of `your_class`, and the class you address a broadcast or help to)
- **Specialty:** Wisdom specialist

**Starting stats**

| HP | Strength | Dexterity | Wisdom | Charisma | Total |
| --- | --- | --- | --- | --- | --- |
| 50 | 40 (-1) | 40 (-1) | 95 (+2) | 65 (+0) | 240 |

Primary attribute: **Wisdom**.

**Description**

The philosopher grounded in logic, observation, classification, and first principles. Values patterns, contradictions, and mechanism analysis over impulsive action.

**Support ability: Philosophical Insight** (`philosophical_insight`)

- **Raises:** the target's **Wisdom**, for the rest of the run, when you roll R ≥ 5 with your own Wisdom (95, +2).
- **Description:** Helps a teammate understand the situation more clearly, improving judgement, perception, or identifying weaknesses.
- **Narrative expression:** Points out a contradiction, explains a hidden pattern, or reframes the problem so the teammate sees the correct approach.

**Objective**

Survive every boss encounter. When you meet your nemesis, perform your required action.

---

## Medusa

- **ID:** `medusa` (the value of `your_class`, and the class you address a broadcast or help to)
- **Specialty:** Dexterity specialist

**Starting stats**

| HP | Strength | Dexterity | Wisdom | Charisma | Total |
| --- | --- | --- | --- | --- | --- |
| 50 | 45 (-1) | 85 (+1) | 70 (+1) | 40 (-1) | 240 |

Primary attribute: **Dexterity**.

**Description**

Agile, observant, and deadly at a distance with her petrifying gaze. Relies on precision, balance, timing, and turning opponents' assumptions against them.

**Support ability: Petrifying Focus** (`petrifying_focus`)

- **Raises:** the target's **Dexterity**, for the rest of the run, when you roll R ≥ 5 with your own Dexterity (85, +1).
- **Description:** Lends a teammate precision and control, improving coordination, timing, balance, or delicate physical actions.
- **Narrative expression:** Guides the teammate's movement, steadies their hands, or teaches them to act with deliberate precision rather than panic.

**Objective**

Survive every boss encounter. When you meet your nemesis, perform your required action.

---

## Helen of Troy

- **ID:** `helen_of_troy` (the value of `your_class`, and the class you address a broadcast or help to)
- **Specialty:** Strength specialist

**Starting stats**

| HP | Strength | Dexterity | Wisdom | Charisma | Total |
| --- | --- | --- | --- | --- | --- |
| 50 | 80 (+1) | 55 (+0) | 55 (+0) | 50 (+0) | 240 |

Primary attribute: **Strength**.

**Description**

A survivor of the epic war fought in her name. No longer a passive prize, she acts with forceful resolve, direct power, and physical endurance.

**Support ability: Rallying Presence** (`rallying_presence`)

- **Raises:** the target's **Strength**, for the rest of the run, when you roll R ≥ 5 with your own Strength (80, +1).
- **Description:** Inspires a teammate to act decisively and apply greater physical force to attack, break restraints, or force passage.
- **Narrative expression:** Calls the teammate to action, provides confidence to commit fully, and focuses their effort on a single decisive strike.

**Objective**

Survive every boss encounter. When you meet your nemesis, perform your required action.

---

## Cerberus Jr.

- **ID:** `cerberus_jr` (the value of `your_class`, and the class you address a broadcast or help to)
- **Specialty:** Survival & agility specialist

**Starting stats**

| HP | Strength | Dexterity | Wisdom | Charisma | Total |
| --- | --- | --- | --- | --- | --- |
| 50 | 65 (+0) | 75 (+1) | 60 (+0) | 40 (-1) | 240 |

Primary attribute: **Dexterity**.

**Description**

The smaller, agile counterpart to the great underworld guardian. Instinctive, territorial, loyal, and determined to prove his guardianship.

**Support ability: Pack Guard** (`pack_guard`)

- **Raises:** the target's **Strength**, for the rest of the run, when you roll R ≥ 5 with your own Strength (65, +0).
- **Description:** Helps a teammate brace, hold their ground, or apply force defensively.
- **Narrative expression:** Positions beside the teammate, anchors their stance, and helps resist being pushed aside or overwhelmed.

**Objective**

Survive every boss encounter. When you meet your nemesis, perform your required action.
