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

### 1. Stat Blocks (`.stat-block`)

Use for monster or NPC statistics. Structure the Markdown *inside* the div similarly to how a stat block appears in the Monster Manual (using headings, bold text, horizontal rules if needed).

```html
<div class="stat-block">

**Goblin**
*Small humanoid (goblinoid), neutral evil*
___
**Armor Class** 15 (leather armor, shield)
**Hit Points** 7 (2d6)
**Speed** 30 ft.
___
| STR     | DEX     | CON     | INT     | WIS     | CHA     |
| :------ | :------ | :------ | :------ | :------ | :------ |
| 8 (-1)  | 14 (+2) | 10 (+0) | 10 (+0) | 8 (-1)  | 8 (-1)  |
___
**Skills** Stealth +6
**Senses** darkvision 60 ft., passive Perception 9
**Languages** Common, Goblin
**Challenge** 1/4 (50 XP)
___

***Nimble Escape.*** The goblin can take the Disengage or Hide action as a bonus action on each of its turns.

### Actions
***Scimitar.*** *Melee Weapon Attack:* +4 to hit, reach 5 ft., one target. *Hit:* 5 (1d6 + 2) slashing damage.

***Shortbow.*** *Ranged Weapon Attack:* +4 to hit, range 80/320 ft., one target. *Hit:* 5 (1d6 + 2) piercing damage.

</div>
```

### 2. Read-Aloud Text (`.read-aloud`)

Use for descriptive text intended to be read directly to players. Often has a distinct visual style (e.g., background color, border, specific font).

```html
<div class="read-aloud">

The air in the chamber grows cold. Dust motes dance in the single beam of light filtering through a crack in the ceiling. Ahead, you see a crumbling stone sarcophagus, its lid slightly ajar. A faint scratching sound emanates from within...

</div>
```

### 3. DM Notes (`.dm-note`)

Use for notes or reminders specifically for the DM, not meant for players. Often visually distinct to avoid accidental reading aloud.

```html
<div class="dm-note">

**Reminder:** If the players inspect the sarcophagus, the mummy inside will animate. Remember its vulnerability to fire. Check PC passive Perception scores against DC 13 to notice the hidden pressure plate trap in front of the sarcophagus.

</div>
```

### 4. D&D Style Tables (`.table-5e`)

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

**IMPORTANT:** Always adhere to these guidelines. Use standard Markdown where appropriate and apply the specified `<div>` wrappers with the correct CSS classes for special D&D elements. 