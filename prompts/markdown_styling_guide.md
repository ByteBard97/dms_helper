# D&D 5e Markdown Styling Guide for LLM Output

This guide MUST be followed when generating responses to ensure consistent D&D 5e styling.

## Standard Markdown

Use standard Markdown for basic formatting:

*   **Headings:** Use `##` or `###` for section titles (e.g., `## **Treasure Found**`).
*   **Emphasis:** Use `**bold**` for emphasis or keywords, and `*italics*` for thoughts or special terms.
*   **Lists:** Use standard bulleted lists (`*` or `-`) or numbered lists (`1.`).
*   **Paragraphs:** Standard paragraph formatting.

## Special D&D 5e CSS Classes

Use these specific CSS classes by wrapping content in `<div>` tags when appropriate.

### 1. Read-Aloud Text (`.read-aloud`)

Use for descriptive text intended to be read directly to players. Often has a distinct visual style (e.g., background color, border, specific font).

```html
<div class="read-aloud">

The air in the chamber grows cold. Dust motes dance in the single beam of light filtering through a crack in the ceiling. Ahead, you see a crumbling stone sarcophagus, its lid slightly ajar. A faint scratching sound emanates from within...

</div>
```

### 2. DM Notes (`.dm-note`)

Use for notes or reminders specifically for the DM, not meant for players. Often visually distinct to avoid accidental reading aloud.

```html
<div class="dm-note">

**Reminder:** If the players inspect the sarcophagus, the mummy inside will animate. Remember its vulnerability to fire. Check PC passive Perception scores against DC 13 to notice the hidden pressure plate trap in front of the sarcophagus.

</div>
```

### 3. D&D Style Tables (`.table-5e`)

Use for tables that should mimic the D&D book style (e.g., encounter tables, treasure tables). Apply the class to the `<table>` element itself or wrap the entire Markdown table in a div with this class. (Exact implementation depends on CSS, but instruct the LLM to use the class).

```html
<div class="table-5e">

| d6 | Encounter           |
|:---|:--------------------|
| 1  | 2d4 Giant Spiders   |
| 2  | 1d6 Goblins         |
| 3  | 1 Owlbear           |
| 4  | Abandoned Campsite  |
| 5  | Hidden Shrine (DC15)|
| 6  | Merchant Caravan    |

</div>
```

## JSON Stat-Blocks

When describing a creature, monster, or NPC, **output a single fenced JSON block** exactly in the structure below—_no additional prose before or after the block_. The UI will automatically detect and render it.

```json
{
  "name": "Goblin",
  "size": "Small",
  "type": "humanoid",
  "alignment": "neutral evil",
  "armor_class": 15,
  "hit_points": 7,
  "speed": "30 ft.",
  "abilities": {
    "str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8
  },
  "senses": "darkvision 60 ft.",
  "languages": "Common, Goblin",
  "challenge": "1/4 (50 XP)",
  "traits": [
    { "name": "Nimble Escape", "desc": "The goblin can take the Disengage or Hide action as a bonus action." }
  ],
  "actions": [
    { "name": "Scimitar",  "desc": "Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 5 (1d6+2) slashing." },
    { "name": "Shortbow", "desc": "Ranged Weapon Attack: +4 to hit, range 80/320 ft., one target. Hit: 5 (1d6+2) piercing." }
  ]
}
```

Guidelines:
- Use the keys exactly as shown; omit any field that doesn't apply.
- Do **not** wrap this JSON in extra Markdown like blockquotes or headings.
- Each creature gets its own fenced block. 