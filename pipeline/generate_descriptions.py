#!/usr/bin/env python3
"""
Generate per-person descriptions for the top 50 people by risk_score using Claude API.
People ranked 51-200 get a short computed description. Saves updated dashboard_data.json.
"""

import json
import os
import time
from collections import defaultdict

import anthropic

DATA_PATH = "dashboard_data.json"

with open(DATA_PATH) as f:
    data = json.load(f)

# Build edge lookup for top communication partners
edges_by_person = defaultdict(list)
for e in data.get("graph", {}).get("edges", []):
    edges_by_person[e["source"]].append((e["target"], e["weight"]))
    edges_by_person[e["target"]].append((e["source"], e["weight"]))

# Build display_name lookup
name_lookup = {}
for p in data["people"]:
    name_lookup[p["person"]] = p.get("display_name") or p["person"].split("@")[0].replace(".", " ").title()

def top_partners(person_email, n=3):
    partners = sorted(edges_by_person[person_email], key=lambda x: -x[1])[:n]
    return [name_lookup.get(e, e.split("@")[0].replace(".", " ").title()) for e, _ in partners]

def topic_list(person, n=3):
    profile = person.get("topic_profile", [])
    cats = []
    seen = set()
    for t in profile:
        c = t.get("category")
        if c and c not in seen:
            cats.append(c)
            seen.add(c)
        if len(cats) >= n:
            break
    return cats

def rarest_topic(person, all_people):
    """Find the topic category fewest other people also have."""
    my_cats = set(topic_list(person, 10))
    if not my_cats:
        return None, 0
    cat_counts = defaultdict(int)
    my_email = person["person"]
    for other in all_people:
        if other["person"] == my_email:
            continue
        for c in set(topic_list(other, 10)):
            cat_counts[c] += 1
    rarest = None
    min_count = float("inf")
    for c in my_cats:
        cnt = cat_counts.get(c, 0)
        if cnt < min_count:
            min_count = cnt
            rarest = c
    return rarest, min_count

people = data["people"]
all_people = people  # reference for rarest topic computation

# Sort by risk_score descending
ranked = sorted(enumerate(people), key=lambda x: -x[1].get("risk_score", 0))

client = anthropic.Anthropic()

for rank_idx, (orig_idx, person) in enumerate(ranked):
    name     = person.get("display_name") or person["person"].split("@")[0].replace(".", " ").title()
    title    = person.get("role") or "Unknown Role"
    kr       = person.get("risk_score", 0)
    pi       = person.get("positional_impact", 0)
    quadrant = person.get("quadrant", "Low Priority")
    perm     = person.get("n_perm_loss_categories", 0)
    topics   = topic_list(person, 3)
    rare_cat, rare_count = rarest_topic(person, all_people)
    partners = top_partners(person["person"])

    if rank_idx < 50:
        prompt = (
            f"Write a 2-3 sentence executive briefing about this Enron employee's organizational risk profile. "
            f"Be specific to this person — reference their actual role, department, and unique risk factors. "
            f"No hyphens. No generic language. Factual and analytical tone.\n\n"
            f"Person: {name}\n"
            f"Title: {title}\n"
            f"Knowledge Risk: {kr*100:.1f}%\n"
            f"Positional Impact: {pi*100:.0f}%\n"
            f"Quadrant: {quadrant}\n"
            f"Top Topics: {', '.join(topics) if topics else 'N/A'}\n"
            f"Rarest Topic: {rare_cat or 'N/A'} with {rare_count} other expert(s)\n"
            f"Permanent Knowledge Losses: {perm}\n"
            f"Top Communication Partners: {', '.join(partners) if partners else 'N/A'}\n\n"
            f"Write the briefing."
        )
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            )
            description = response.content[0].text.strip().replace("-", "\u2011")
            print(f"[{rank_idx+1:>2}] {name}")
            print(f"     {description}")
            print()
            # Small delay to avoid rate limits
            time.sleep(0.3)
        except Exception as e:
            print(f"[{rank_idx+1:>2}] {name} — API error: {e}")
            description = f"{quadrant}: {kr*100:.1f}% knowledge risk, {pi*100:.0f}% positional impact."
    else:
        # Computed description for rank 51+
        topic_str = topics[0] if topics else "their domain"
        if quadrant == "Low Priority":
            description = f"Standard succession risk in {topic_str}. Knowledge is broadly shared and positional impact is limited."
        elif quadrant == "Silent Threat":
            description = f"Carries {kr*100:.1f}% knowledge risk in {topic_str} despite a lower positional footprint. Knowledge concentration warrants monitoring."
        elif quadrant == "Replaceable Executive":
            description = f"Holds {pi*100:.0f}% positional impact but knowledge in {topic_str} is well distributed across the organization."
        else:
            description = f"{quadrant}: {kr*100:.1f}% knowledge risk, {pi*100:.0f}% positional impact in {topic_str}."

    people[orig_idx]["description"] = description

with open(DATA_PATH, "w") as f:
    json.dump(data, f, indent=2)

print(f"\nSaved descriptions for {len(people)} people to {DATA_PATH}.")
