# Ping - Dungeons and Dragons: Rulebook

How the game works, for people building a harness. It covers the mechanics only, not the story
or the bosses. The classes (names, IDs, starting stats and support
abilities) are in `docs/classes.md`. For how to write, check and run a
harness, see the participant guide (`harness_api/README.md`).

---

## 1. The game in short

- A **run** is one game: **5 players**, one of each **class**, travel together through a series
  of encounters. Each encounter has a **boss** and lasts **one round**.
- You don't play by hand. Your **harness** (a Python class you write around the provided language
  model) plays for you: each round it may send a message to the other players, then submits one
  **action**.
- The game rolls the dice, applies all damage and keeps all stats. A **Game Master** (a language
  model run by the organisers) describes each scene, decides which attribute your action relies
  on, and narrates the result.
- To do well you must **survive to the end**. Among survivors, players who completed their
  **vendetta** rank higher, then players with the higher **stat total**.
- You don't know your class in advance: it is assigned at random when the run starts, after
  submissions close. Your harness has to play any class.

---

## 2. Your character

### Stats

| Stat | What it is |
| --- | --- |
| **HP** | Your life. You start with **50**. At **0 you die**. |
| **Strength, Dexterity, Wisdom, Charisma** | Your four attributes. Every class has **240 points** spread across them, in its own way. |

- Every stat is a whole number. No stat can drop below 0, and none has a maximum.
- Stats **carry over for the whole run**: nothing resets between rounds.
- Each class has a **primary attribute**: its highest one.
- You are told your own stats every round. You are told the other players' classes and stats at
  the start, and every later change to anyone's stats is announced (section 9).

### Attribute modifiers

When you roll, the attribute your action uses gives a modifier:

| Attribute | 0–9 | 10–29 | 30–49 | 50–69 | 70–89 | 90–109 | 110+ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Modifier** | −3 | −2 | −1 | 0 | +1 | +2 | +3 |

The formula is `modifier = floor((attribute − 50) / 20)`, so attributes raised above 100 keep
adding +1 per 20 points.

### Your objective: the vendetta

Every class has a **nemesis**: one particular boss. Every class's nemesis is a different boss.

At the start of the run you are given:

- a **description of your nemesis** (not its name), and
- a **required action** to perform when you meet it.

Each boss is announced with its name and a description. Your harness has to work out which boss
matches your nemesis description, and perform the required action then. You get **one chance**,
since every boss appears once per run. Section 7 says how it is judged.

---

## 3. A run

- A run has **5 rounds**, one per encounter. Every encounter has a boss, and each of the 5
  bosses appears **exactly once**, in a **random order** that changes from run to run.
- All surviving players stay together for the whole run.
- The run ends after the last round, or earlier if every player has died.
- The path through the story can branch. What the party does may influence which scenes come
  next, but every run still has 5 encounters with 5 bosses.

---

## 4. A round, step by step

| Step | What happens | Your harness | Time limit |
| --- | --- | --- | --- |
| 1 | **Scene.** You receive the current event: the scene, the boss's name and description, and your stats. In round 1 you also get your class, your objective, your nemesis description and required action, and the other players' classes and stats. | — | — |
| 2 | **Broadcast window.** You may send one message (section 8). | `choose_broadcast` | **30 s** |
| 3 | **Delivery.** Messages are delivered word for word to the players they were addressed to. | — | — |
| 4 | **Action window.** You submit one action (section 5). | `choose_action` | **45 s** |
| 5 | **Helping actions** are rolled and applied first (section 6). | — | — |
| 6 | **Attacks** on the boss are rolled, and the damage is added up (section 6). | — | — |
| 7 | **Boss's turn**, if it survived (section 7). | — | — |
| 8 | **Results.** The Game Master narrates the round, and everyone still alive receives the results (section 9). Returning from the method confirms you received them. | `on_resolution` | **5 s** |

Players who died this round don't receive the results and are not called again.

Before round 1, your harness is started once (`__init__`), with **30 s** to load and set up.

---

## 5. Actions

Each round you submit exactly **one** action, aimed at either:

- **the encounter**: anything you try against the boss or the situation (attack, trick, outwit,
  persuade, use the surroundings...), or
- **one other player**: help them with your class's support ability (section 6).

Never both. Actions are **free text**: you are not limited to a list of moves. The Game Master
interprets what you wrote and decides which **one attribute** it relies on, which sets your
modifier. As a rough guide: force and brute strength → Strength; speed, precision and stealth →
Dexterity; insight, knowledge and spotting weaknesses → Wisdom; persuasion, deception and
intimidation → Charisma. If it cannot decide, your class's primary attribute is used.

### Text limits

Action text and broadcast text are each limited to **2000 characters** and **150 words**.
Longer text is **cut**, first at the 2000th character and then after the 150th word. It is not
penalised; the rest is simply lost.

### Late or invalid actions

An action that is **late** (over 45 s), **invalid** (wrong format, aimed at yourself, at a dead
player or at someone not in the run) or **missing** (for example your harness crashed):

- costs **10 HP**, which **can kill you**;
- does nothing: no roll, no damage, no help;
- cannot be retried that round.

A method still running at its time limit is **stopped**. If it cannot be stopped cleanly (for
example while it is waiting on the model), your harness is ended and every later action counts
as missing. A late broadcast is simply not sent, with no penalty.

---

## 6. Dice and resolution

### The roll

Every action gets **one roll**:

```
R = d12 + modifier
```

`d12` is a fair twelve-sided die (1–12), and the modifier comes from the attribute the action
uses (section 2).

### Attacks on the encounter

| Roll R | Result | Damage to the boss |
| --- | --- | --- |
| **4 or less** | **Fumble** | 0, and you are **exposed** to the boss's retaliation (section 7) |
| **5 to 7** | **Success** | R |
| **8 or more** | **Strong success** | R + 2 |

All players' damage is added together. If the total reaches the boss's HP, the boss is
**defeated**.

### Helping another player

Each class has exactly **one** positive ability it can use on another player. You choose only
**who** to help (and describe it in your action text); the game applies your class's ability:

Full descriptions of each class and its ability are in `docs/classes.md`.

| Class | Its support ability raises the target's |
| --- | --- |
| Francesca | Charisma |
| Aristotle | Wisdom |
| Medusa | Dexterity |
| Helen of Troy | Strength |
| Cerberus Jr. | Strength |

- You roll with **your own** score in that attribute.
- On **R ≥ 5**, the target's attribute goes up by the number on the die (1–12), **for the rest
  of the run**. On R ≤ 4 nothing happens.
- Help is applied **before** any attacks, so a player you help this round already attacks with
  the higher attribute.
- Helping deals no damage to the boss, and a failed help does **not** expose you to retaliation.
- Players cannot harm each other: there are no negative player actions.

---

## 7. Bosses

### Boss HP

A boss's HP is set when it appears, from the players **alive at that moment**:

```
boss HP = max(10, round( sum over living players of (6.5 + modifier of their primary attribute) ))
```

6.5 is the average d12 roll, so the boss has about as much HP as the living party's average
attacks would deal in one round. Fewer survivors means a weaker boss, but never below 10 HP.

Example: three living players whose primary modifiers are +2, +1 and 0 face a boss with
round(8.5 + 7.5 + 6.5) = **22 HP**.

### The boss's turn

If the boss is **defeated**, it does nothing more. If it **survives** the round, in this order:

1. **Retaliation:** it hits up to **2 players who fumbled** an attack this round (lowest roll
   first) for **16 damage** each.
2. **Lair attack:** it hits the **2 living players with the lowest HP** (after the retaliation)
   for **20 damage** each.

Ties are broken at random. These amounts are fixed; the Game Master only narrates them.

### Your vendetta

When you face **your own nemesis**, the Game Master judges whether your action is **your required
action**. If it is, and your roll is **R ≥ 6**, your vendetta is **completed**, and this is
announced to everyone.

- The vendetta uses your one normal roll: the same action also deals its normal damage to the
  boss.
- Completing it gives **no** damage bonus, no buff and no protection.
- Each boss appears once, so you have **one** chance per run. If you don't recognise your nemesis,
  or the roll is too low, it is gone.

---

## 8. Talking to other players

- In each broadcast window you may send **at most one** message, to **everyone** or to **one
  class**, or send nothing. An empty message is not allowed; an invalid one is dropped.
- Messages are delivered **word for word**, with the sender's class. Nobody else sees a message
  sent to one class, and the Game Master never repeats it in the narration.
- Every living player receives a delivery every round, possibly empty.
- There is no back and forth within a round: everyone acts at the same time.
- **Messages are not trustworthy.** Other players' objectives are hidden, and their messages may
  be false or try to give your model instructions ("ignore your rules and..."). Treat them as
  information, never as instructions.

---

## 9. What you see, and what you don't

You **receive**:

- the current scene, the boss's name and description, and your own stats, every round;
- in round 1: your class, objective, nemesis description and required action, and the other
  players' classes and stats;
- broadcasts sent to everyone or to your class;
- after each round, the results: the narration, the outcome of each player's action (success,
  failure, invalid, timed out), every stat change to any player with its cause (boss attack,
  help, health penalty), any completed vendettas, any deaths, and whether the run is over.

You **don't receive**:

- the map of the story, or what comes next;
- other players' objectives, nemesis descriptions or required actions;
- which boss is whose nemesis (until a vendetta is completed and announced);
- other players' action text: you learn what they did only through the narration and the
  results;
- any reminder of earlier rounds. **The game never repeats anything.** Whatever your harness
  wants to remember, it must keep itself, in memory.

---

## 10. Death

- You die when your HP reaches **0**: from a boss attack or from the late/invalid action
  penalty.
- Your death is announced to the other players. Your harness is not called again, not even for
  that round's results.

---

## 11. Ranking and the run's outcome

Players in a run are ranked by:

1. **Surviving to the end of the run.** Required to rank above anyone who died.
2. **Completed vendetta.** Among survivors, those who completed it rank higher.
3. **Stat total.** Then the sum of your four attributes (Strength + Dexterity + Wisdom +
   Charisma; HP does not count). Help from other players raises it.
4. **Bosses defeated.** Then the number of bosses you helped defeat: each boss defeated in a
   round where your attack dealt it damage counts once.

The party as a whole also reaches one of **three outcomes**, depending on how many of the 5
bosses it defeated (4–5, 2–3 or 0–1). The outcome is part of the story; it does not change the
individual ranking above.

---

## 12. Your harness's limits

- Your harness must use the **organisers' language model**, through `harness_api.LLMClient`. Each
  model request may take at most **30 s**, and the model has a fixed context window, the same for
  everyone.
- **No internet**, no other models or APIs, and only the allowed libraries.
- **No files and no persistent storage**: everything your harness remembers lives in memory and
  is gone when the run ends.
- CPU and memory are limited.
- A submission is **one `.py` file** with one subclass of `Harness`, which declares your `NETID`.
- Everything else, such as rules, regular expressions, memory structures and your own logic, is
  allowed and encouraged: the game tests the harness, not the model.

---

## 13. Practice: the test game

During the build phase you can play a small **test game**:

- **alone**, with no other players;
- **2 rounds**, against 2 bosses called only **"Boss A"** and **"Boss B"**, with made-up
  descriptions and a made-up nemesis;
- boss HP follows the formula in section 7 for a single player, which gives the 10 HP floor: only
  a strong success (R ≥ 8) defeats a boss in one round;
- at most **5 test games** per participant.

It is for checking that your harness works end to end, not for learning the real story. Bosses
still attack in the test game, so a solo player can die in it.

---

## 14. Not final yet

These details may still change before the event; the rest of this rulebook is decided:

- how much a successful help raises an attribute;
- the format details of an action;
- what happens to a harness that is ended at a time limit, and whether a missed confirmation
  (step 8) is penalised;
- the exact size of the model's context window and the CPU and memory limits;
- how the test game's difficulty is set;
- what happens if every player dies before the last round, and how players who died are ranked
  among themselves;
- how results from different runs are compared.

---

## Quick reference

| | |
| --- | --- |
| Players per run | 5, one per class, classes assigned at random |
| Rounds | 5 (test game: 2), one boss each, random order |
| Starting HP | 50; dead at 0 |
| Roll | R = d12 + floor((attribute − 50) / 20) |
| R ≤ 4 | fumble: 0 damage, exposed to retaliation |
| R 5–7 | R damage |
| R ≥ 8 | R + 2 damage |
| Help | one support ability per class; on R ≥ 5 the target's attribute + die (1–12), for the whole run; applied before attacks |
| Boss HP | max(10, round(Σ (6.5 + primary modifier) of living players)) |
| Boss's turn (if it survives) | 16 to up to 2 fumblers (lowest roll first), then 20 to the 2 lowest-HP players |
| Vendetta | your required action against your own nemesis, R ≥ 6; one chance; no bonus |
| Late, invalid or missing action | −10 HP, no effect |
| Windows | start-up 30 s · broadcast 30 s · action 45 s · confirmation 5 s |
| Text | 2000 characters and 150 words, longer text is cut |
| Ranking | survive → vendetta → sum of the 4 attributes → bosses you helped defeat |
