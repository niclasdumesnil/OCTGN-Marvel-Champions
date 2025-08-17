import os
import argparse
import json
from lxml import etree as ET

# Dictionnaire de mapping XML -> JSON
XML_TO_JSON_MAP = {
    "CardNumber": "code",
    "Position": "position",
    "Quantity": "quantity",
    "DuplicateOf": "duplicate_of",
    "Faction": "faction_code",
    "Type": "type_code",
    "Owner": "set_code",
    "Stage": "stage",
    "Standard": "standard",
    "Expert": "expert",
    "HandSize": "hand_size",
    "Thwart": "thwart",
    "ThwartCost": "thwart_cost",
    "Attack": "attack",
    "AttackCost": "attack_cost",
    "Defense": "defense",
    "DefenseCost": "defense_cost",
    "Recovery": "recover",
    "Scheme": "scheme",
    "Boost": "boost",
    "Cost": "cost",
    "Resource_Mental": "resource_mental",
    "Resource_Physical": "resource_physical",
    "Resource_Energy": "resource_energy",
    "Resource_Wild": "resource_wild",
    "HP": "health",
    "HP_Per_Hero": "health_per_hero",
    "BaseThreat": "base_threat",
    "BaseThreatFixed": "base_threat_fixed",
    "Threat": "threat",
    "EscalationThreat": "escalation_threat",
    "EscalationThreatFixed": "escalation_threat_fixed",
    "Scheme_Acceleration": "scheme_acceleration",
    "Scheme_Crisis": "scheme_crisis",
    "Scheme_Hazard": "scheme_hazard",
    "Scheme_Boost": "scheme_boost",
    "Attribute": "traits",
    "Text": "text",
    "Quote": "flavor",
    "Unique": "is_unique",
    # alternate/back_link géré à part
}

# Exceptions : liste de tuples (propriété, valeur) pour lesquelles la carte ne doit pas être ajoutée au JSON
EXCLUDED_CARDS = [
    ("Type", "fm_hero_setup"),
    ("Type", "fm_encounter_setup"),
]

parser = argparse.ArgumentParser()
parser.add_argument('--setxml', type=str, required=True, help='Chemin du set.xml à convertir')
args = parser.parse_args()

setxml_path = args.setxml
set_dir = os.path.dirname(setxml_path)

tree = ET.parse(setxml_path)
root = tree.getroot()

cards_elem = root.find('cards')
if cards_elem is None:
    print("Aucune section <cards> trouvée dans le set.xml.")
    exit(1)

# Trouver le pack_code (owner du fm_hero_setup)
pack_code = None
for card_elem in cards_elem.findall('card'):
    for prop in card_elem.findall('property'):
        if prop.get('name') == "Type" and prop.get('value') == "fm_hero_setup":
            for prop2 in card_elem.findall('property'):
                if prop2.get('name') == "Owner":
                    pack_code = prop2.get('value')
if not pack_code:
    print("Impossible de déterminer le pack_code (owner de fm_hero_setup)")
    exit(1)

# Génération des cartes JSON par owner
owner_cards = {}

for card_elem in cards_elem.findall('card'):
    # Récupère les propriétés
    properties = {}
    for prop in card_elem.findall('property'):
        pname = prop.get('name')
        pvalue = prop.get('value')
        if pname and pvalue:
            properties[pname] = pvalue

    # Exceptions : on saute les cartes à exclure
    if any(properties.get(exc[0]) == exc[1] for exc in EXCLUDED_CARDS):
        continue

    # Construction de la carte principale
    card_data = {}
    card_data['pack_code'] = pack_code
    card_data['octgn_id'] = card_elem.get('id')
    card_data['name'] = card_elem.get('name')
    if card_elem.get('size'):
        card_data['size'] = card_elem.get('size')
    for pname, pvalue in properties.items():
        json_key = XML_TO_JSON_MAP.get(pname, pname.lower())
        card_data[json_key] = pvalue

    owner = card_data.get('set_code', 'unknown_owner')
    if owner not in owner_cards:
        owner_cards[owner] = []
    
    # Gestion de l'alternate
    alternate_elem = card_elem.find('alternate')
    if alternate_elem is not None:
        # Génère la carte alternate
        alt_properties = {}
        for prop in alternate_elem.findall('property'):
            pname = prop.get('name')
            pvalue = prop.get('value')
            if pname and pvalue:
                alt_properties[pname] = pvalue
        alt_card = {}
        alt_card['pack_code'] = pack_code
        alt_card['octgn_id'] = card_data['octgn_id']
        alt_card['name'] = alternate_elem.get('name')
        if alternate_elem.get('size'):
            alt_card['size'] = alternate_elem.get('size')
        for pname, pvalue in alt_properties.items():
            json_key = XML_TO_JSON_MAP.get(pname, pname.lower())
            alt_card[json_key] = pvalue

        # Ajoute le back_link à la carte principale
        if 'code' in alt_card:
            card_data['back_link'] = alt_card['code']

        # Ajoute la carte principale puis l'alternate juste après
        owner_cards[owner].append(card_data)
        owner_cards[owner].append(alt_card)
    else:
        owner_cards[owner].append(card_data)

# Écrit un fichier JSON par owner, en remplaçant _nemesis par _encounter dans le nom du fichier
for owner, cards in owner_cards.items():
    json_filename = f"{owner}.json"
    if "_nemesis" in json_filename:
        json_filename = json_filename.replace("_nemesis", "_encounter")
    json_path = os.path.join(set_dir, json_filename)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)

print(f"Conversion terminée. Fichiers JSON créés dans {set_dir}")