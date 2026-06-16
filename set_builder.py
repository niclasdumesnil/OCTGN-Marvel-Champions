import json
import os
import re
from os import path
import argparse
from lxml import etree as ET

# ---------------------------------------------------------------------------
# Overrides from octgn_overrides.json (§8 du SKILL.md)
# ---------------------------------------------------------------------------
OVERRIDES = {}  # Populated by loadOverrides()
ALL_PACK_CARDS = []  # Populated by load_all_pack_cards()

def load_all_pack_cards():
    """Load all cards from all valid runFileList into a global list."""
    global ALL_PACK_CARDS
    ALL_PACK_CARDS = []
    for curFile in runFileList:
        if path.exists(curFile):
            try:
                with open(curFile, encoding="utf-8") as jf:
                    data = json.load(jf)
                    if isinstance(data, list):
                        ALL_PACK_CARDS.extend(data)
            except Exception as e:
                print(f"[CACHE] Error loading {curFile}: {e}")

def loadOverrides(pack_code):
    """Load per-pack overrides from octgn_overrides.json.
    Returns the override dict for the given pack_code, or empty dict."""
    overrides_path = os.path.join(
        "c:", os.sep, "github", "marvelsdb_fanmade_data", "octgn_overrides.json"
    )
    if not os.path.exists(overrides_path):
        print(f"[OVERRIDES] File not found: {overrides_path}")
        return {}
    try:
        with open(overrides_path, encoding="utf-8") as f:
            all_overrides = json.load(f)
        pack_overrides = all_overrides.get(pack_code, {})
        if pack_overrides:
            print(f"[OVERRIDES] Loaded overrides for pack '{pack_code}'")
        return pack_overrides
    except Exception as e:
        print(f"[OVERRIDES] Error loading overrides: {e}")
        return {}

def getCardOverride(card_code):
    """Return the card override dict for a given card code, or None."""
    for co in OVERRIDES.get("card_overrides", []):
        if co.get("code") == str(card_code):
            return co
    return None

def getScenarioOverride(set_code):
    """Return the scenario override dict for a given villain set_code, or None."""
    for so in OVERRIDES.get("scenario_overrides", []):
        if so.get("set_code") == set_code:
            return so
    return None

# Set types considered as "hero" for ignore_heroes
HERO_SET_TYPES = {'hero', 'hero_special'}
# Set types considered as "scenario" for ignore_scenarios
SCENARIO_SET_TYPES = {'villain', 'modular', 'standard', 'expert'}

def shouldIgnoreCard(set_code, set_type_map):
    """Check if a card should be ignored based on ignore_heroes/ignore_scenarios pack overrides.
    Returns True if the card should be skipped."""
    if not OVERRIDES:
        return False
    set_type = set_type_map.get(set_code, "")
    is_nemesis = set_code.endswith("_nemesis")
    if OVERRIDES.get("ignore_heroes") and (set_type in HERO_SET_TYPES or is_nemesis):
        return True
    if OVERRIDES.get("ignore_scenarios") and (set_type in SCENARIO_SET_TYPES and not is_nemesis):
        return True
    return False

# --- EXCEPTIONS MIGRÉES VERS octgn_overrides.json ---
# SETUP_EXCEPTIONS, ACTIVATION_ORDER_*, OWNER_EXCEPTIONS
# sont désormais gérés via les card_overrides et owner_overrides dans octgn_overrides.json


# Roman numeral to arabic conversion for stages (§5.9)
ROMAN_TO_ARABIC = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5"}

# ---------------------------------------------------------------------------
# Data-driven property mapping (§5 du SKILL.md)
# (xml_property_name, json_key, category)
# Categories: "always", "star", "boolean", "resource", "text", "stat"
# ---------------------------------------------------------------------------
PROPERTY_MAP = [
    # §5.1 Identifiers & Metadata
    ("CardNumber",   "code",         "always"),
    ("Position",     "position",     "always"),
    ("Quantity",     "quantity",     "always"),
    ("Type",         "type_code",    "always"),
    ("Faction",      "faction_code", "always"),
    ("Owner",        "set_code",     "always"),
    # §5.2 Costs & Health
    ("Cost",         "cost",         "stat"),
    ("HP",           "health",       "stat"),
    ("HandSize",     "hand_size",    "stat"),
    # §5.3 Combat & Intervention
    ("Attack",       "attack",       "stat"),
    ("AttackCost",   "attack_cost",  "stat"),
    ("Thwart",       "thwart",       "stat"),
    ("ThwartCost",   "thwart_cost",  "stat"),
    ("Defense",      "defense",      "stat"),
    ("Recovery",     "recover",      "stat"),
    ("Scheme",       "scheme",       "stat"),
    ("Scheme_Acceleration", "scheme_acceleration", "stat"),
    ("Boost",        "boost",        "stat"),
    # §5.5 Threat
    ("BaseThreat",         "base_threat",         "stat"),
    ("EscalationThreat",   "escalation_threat",   "stat"),
    ("Threat",             "threat",              "stat"),
    # §5.6 Booleans
    ("Unique",              "is_unique",              "boolean"),
    ("HP_Per_Hero",         "health_per_hero",        "boolean"),
    ("BaseThreatFixed",     "base_threat_fixed",      "boolean"),
    ("EscalationThreatFixed", "escalation_threat_fixed", "boolean"),
    # §5.7 Resources (only if >= 1)
    ("Resource_Physical", "resource_physical", "resource"),
    ("Resource_Mental",   "resource_mental",   "resource"),
    ("Resource_Energy",   "resource_energy",   "resource"),
    ("Resource_Wild",     "resource_wild",     "resource"),
]

# Setup type mapping: card_set_type_code -> OCTGN setup Type value (§3)
SETUP_TYPE_MAP = {
    "hero": "fm_hero_setup",
    "hero_special": "fm_hero_setup",
    "nemesis": "fm_encounter_setup",
    "modular": "fm_encounter_setup",
    "villain": "fm_villain_setup",
    "standard": "fm_encounter_setup",
    "expert": "fm_encounter_setup",
}

# Ajout de l'argument --packcode pour spécifier le code du pack à traiter
parser = argparse.ArgumentParser()
parser.add_argument('--packcode', type=str, required=True, help='Code du pack à traiter (ex: manifold_by_bluehg)')
parser.add_argument('--herofanmade', action='store_true', help='Indique si le set est un héros FanMade')
parser.add_argument('--obligationsetup', action='store_true', help='Ajoute DefaultSetupPile=Nemesis pour les obligations')
parser.add_argument('--header', action='store_true', help='Ajoute le contenu de header.xml avant la première carte du set')
parser.add_argument('--discardpilesetup', type=str, default=None, help="Ajoute DefaultDiscardPile=Special Discard pour les cartes dont l'owner correspond à la valeur donnée")
args = parser.parse_args()

# On force la valeur de PACK_CODE en minuscules
PACK_CODE = args.packcode.lower()
HERO_FANMADE = args.herofanmade
OBLIGATION_SETUP = args.obligationsetup
HEADER = args.header
DISCARDPILE_SETUP = args.discardpilesetup

# Load overrides for this pack
OVERRIDES = loadOverrides(PACK_CODE)

print(f'fm_{PACK_CODE}')
xmlSet = None
packName = None
runFileList = [
    os.path.join("datapack", PACK_CODE + ".json"),
    os.path.join("datapack", PACK_CODE + "_encounter.json")
]
print("runFileList:", runFileList)
print("HeroFanMade:", HERO_FANMADE)
print("ObligationSetup:", OBLIGATION_SETUP)
print("Header:", HEADER)
print("DiscardPileSetup:", DISCARDPILE_SETUP)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def getPack(set_code):
    pack_path = os.path.join("datapack", f"{set_code}-pack.json")
    with open(pack_path, encoding="utf-8") as pack_json_file:
        packData = json.load(pack_json_file)
        if isinstance(packData, dict):
            packData = [packData]
        for i in packData:
            if isinstance(i, dict) and i.get('code') == set_code:
                return i

def findAlt(data, findValue):
    # First search in data (current file)
    for i in data:
        if i['code'] == findValue:
            return i
    # Fallback to searching ALL_PACK_CARDS (all files in pack)
    for i in ALL_PACK_CARDS:
        if i['code'] == findValue:
            return i
    return None

def loadSetTypeMap():
    """Load set type metadata from sets_fanmade.json and sets.json."""
    set_type_map = {}
    for sets_file in ["sets_fanmade.json", "sets.json"]:
        sets_path = os.path.join("datapack", sets_file)
        if not os.path.exists(sets_path):
            alt_path = os.path.join("c:", os.sep, "github", "marvelsdb_fanmade_data", sets_file)
            if os.path.exists(alt_path):
                sets_path = alt_path
        if os.path.exists(sets_path):
            with open(sets_path, encoding="utf-8") as sf:
                for s in json.load(sf):
                    set_type_map[s.get("code", "")] = s.get("card_set_type_code", "")
    return set_type_map

def loadSetNameMap():
    """Load set name -> code mapping from sets_fanmade.json and sets.json.
    Returns dict {normalized_name: code} for resolving set names to codes."""
    name_map = {}
    for sets_file in ["sets_fanmade.json", "sets.json"]:
        sets_path = os.path.join("datapack", sets_file)
        if not os.path.exists(sets_path):
            alt_path = os.path.join("c:", os.sep, "github", "marvelsdb_fanmade_data", sets_file)
            if os.path.exists(alt_path):
                sets_path = alt_path
        if os.path.exists(sets_path):
            with open(sets_path, encoding="utf-8") as sf:
                for s in json.load(sf):
                    name = s.get("name", "").strip()
                    code = s.get("code", "")
                    if name and code:
                        name_map[name.lower()] = code
    return name_map

def loadOctgnSetupMap():
    """Load the official OCTGN encounter setup map from the official set.xml.
    Returns dict {normalized_name: owner_code} (e.g. 'experimental weapons' -> 'exper_weapon')."""
    octgn_map = {}
    official_set_path = os.path.join(
        os.path.expanduser("~"),
        "AppData", "Local", "Programs", "OCTGN", "Data", "GameDatabase",
        "055c536f-adba-4bc2-acbf-9aefb9756046", "Sets",
        "055c536f-adba-4bc2-acbf-300000000000", "set.xml"
    )
    if not os.path.exists(official_set_path):
        print(f"[OCTGN MAP] Official set.xml not found at {official_set_path}")
        return octgn_map
    try:
        tree = ET.parse(official_set_path)
        root = tree.getroot()
        for card in root.iter('card'):
            card_name = card.get('name', '').strip()
            owner = None
            for prop in card.findall('property'):
                if prop.get('name') == 'Owner':
                    owner = prop.get('value', '')
            if card_name and owner:
                octgn_map[card_name.lower()] = owner
        print(f"[OCTGN MAP] Loaded {len(octgn_map)} official encounter setups")
    except Exception as e:
        print(f"[OCTGN MAP] Error loading official set.xml: {e}")
    return octgn_map

def convert_stage(stage_value):
    """Convert Roman numeral stages to arabic. Keep 1A/1B/2A/2B as-is."""
    if stage_value is None:
        return None
    s = str(stage_value).strip()
    if s in ROMAN_TO_ARABIC:
        return ROMAN_TO_ARABIC[s]
    return s

def get_card_size(type_code, faction_code=""):
    """Determine the OCTGN size attribute for a card (§4)."""
    type_code = type_code.lower() if type_code else ""
    if type_code == 'villain':
        return 'VillainCard'
    if type_code in ('main_scheme', 'side_scheme'):
        return 'SchemeCard'
    if type_code == 'player_side_scheme':
        return 'PlayerSchemeCard'
    if type_code in ('obligation', 'environment', 'attachment', 'minion', 'treachery'):
        return 'EncounterCard'
    return None


# ---------------------------------------------------------------------------
# Property generation (§5)
# ---------------------------------------------------------------------------

def add_property(parent_elem, name, value):
    """Add a <property> element. Use inner text for multiline Text/Quote."""
    if value is None:
        return
    str_val = str(value)
    if str_val.strip() == "":
        return
    # For Text and Quote that contain newlines, use inner text node (§5.8)
    if name in ("Text", "Quote") and "\n" in str_val:
        prop = ET.SubElement(parent_elem, 'property')
        prop.set('name', name)
        prop.text = str_val
    else:
        prop = ET.SubElement(parent_elem, 'property')
        prop.set('name', name)
        prop.set('value', str_val)


def get_property_value(card, xml_name, json_key, category):
    """Extract and format a property value from a card dict per SKILL.md §5."""
    value = card.get(json_key)
    if value is None:
        return None

    if category == "star":
        # §5.4: Only emit if true
        if value is True or str(value).lower() == "true":
            return "True"
        return None

    if category == "boolean":
        # §5.6: Convert to True/False
        if value is True or str(value).lower() == "true":
            return "True"
        elif value is False or str(value).lower() == "false":
            return "False"
        return None

    if category == "resource":
        # §5.7: Only if >= 1
        try:
            if int(value) >= 1:
                return str(int(value))
        except (ValueError, TypeError):
            pass
        return None

    if category == "text":
        str_val = str(value).strip()
        if str_val == "":
            return None
        return str_val  # lxml handles XML escaping natively

    if category == "stat":
        # Allow 0 values for stats (cost=0 is valid)
        str_val = str(value).strip()
        if str_val == "":
            return None
        return str_val

    if category == "always":
        str_val = str(value).strip()
        if str_val == "":
            return None
        # Owner must be lowercase (§3)
        if xml_name == "Owner":
            if str_val in OVERRIDES.get('owner_overrides', []):
                return ""
            return str_val.lower()
        return str_val

    return str(value) if value is not None else None


def get_default_setup_pile(card):
    """Determine the DefaultSetupPile value for a card (§5.9)."""
    type_code = (card.get("type_code") or "").lower()
    set_code = card.get("set_code", "")

    if type_code == "villain":
        return "Villain"
    if type_code == "main_scheme":
        return "Scheme"
    # All cards in a nemesis set (§5.9)
    if set_code.endswith("_nemesis"):
        return "Nemesis"
    # Obligation in a hero set (not a nemesis set)
    if type_code == "obligation" and not set_code.endswith("_nemesis"):
        if OBLIGATION_SETUP or HERO_FANMADE:
            return "Nemesis"
    return None


def buildXmlProps(propDict, xmlElement):
    """Build all XML properties for a card following SKILL.md §5 ordering."""



    # DefaultSetupPile (§5.9) — comes before other properties
    card_override = getCardOverride(propDict.get('code', ''))
    # §8 Override: force DefaultSetupPile from card override
    if card_override and 'default_setup_pile' in card_override:
        add_property(xmlElement, 'DefaultSetupPile', card_override['default_setup_pile'])
        print(f"[OVERRIDES] Card {propDict.get('code')}: DefaultSetupPile -> {card_override['default_setup_pile']}")
    # §8 Override: health_override
    if card_override and 'health_override' in card_override:
        propDict['health'] = card_override['health_override']
        print(f"[OVERRIDES] Card {propDict.get('code')}: health -> {card_override['health_override']}")
    else:
        setup_pile = get_default_setup_pile(propDict)
        if setup_pile:
            add_property(xmlElement, 'DefaultSetupPile', setup_pile)

    # Iterate through ordered property map (§5.1 - §5.7)
    for xml_name, json_key, category in PROPERTY_MAP:
        value = get_property_value(propDict, xml_name, json_key, category)
        add_property(xmlElement, xml_name, value)

    # --- Extra scheme properties not in the standard map ---
    if 'scheme_crisis' in propDict:
        add_property(xmlElement, 'Scheme_Crisis', str(propDict['scheme_crisis']))
    if 'scheme_hazard' in propDict:
        add_property(xmlElement, 'Scheme_Hazard', str(propDict['scheme_hazard']))
    if 'scheme_boost' in propDict:
        add_property(xmlElement, 'Scheme_Boost', str(propDict['scheme_boost']))

    # --- Check card overrides for ignore_fields (§8) ---
    # card_override already loaded above for DefaultSetupPile
    ignore_fields = set()
    if card_override:
        ignore_fields = set(card_override.get('ignore_fields', []))
        if ignore_fields:
            print(f"[OVERRIDES] Card {propDict.get('code')}: ignoring fields {ignore_fields}")

    # §5.8 Text & Traits — Attribute
    if 'traits' in propDict and 'traits' not in ignore_fields:
        add_property(xmlElement, 'Attribute', str(propDict['traits']))

    # §5.8 Text — combining attack_text, scheme_text, text, boost_text
    if 'text' not in ignore_fields:
        text_parts = []
        if 'attack_text' in propDict:
            text_parts.append(propDict['attack_text'])
        if 'scheme_text' in propDict:
            text_parts.append(propDict['scheme_text'])
        if 'text' in propDict:
            text_parts.append(propDict['text'])
        if 'boost_text' in propDict:
            text_parts.append(propDict['boost_text'])
        if text_parts:
            combined_text = '\n'.join(text_parts)
            # §8 Override: prepend_text
            if card_override and 'prepend_text' in card_override:
                combined_text = card_override['prepend_text'] + combined_text
                print(f"[OVERRIDES] Card {propDict.get('code')}: prepending '{card_override['prepend_text']}' to text")
            add_property(xmlElement, 'Text', combined_text)

    # §5.8 Quote
    if 'flavor' in propDict and 'flavor' not in ignore_fields:
        add_property(xmlElement, 'Quote', propDict['flavor'])

    # §5.9 Stage handling (scenario cards)
    stage_raw = propDict.get('stage')
    if stage_raw is not None:
        stage_converted = convert_stage(stage_raw)
        add_property(xmlElement, 'Stage', stage_converted)
        # Standard / Expert for villain cards
        type_code = propDict.get('type_code', '')
        if type_code == 'villain':
            try:
                stage_num = int(stage_converted)
            except (ValueError, TypeError):
                stage_num = None
            if stage_num == 1:
                add_property(xmlElement, 'Standard', 'True')
                add_property(xmlElement, 'Expert', 'False')
            elif stage_num == 2:
                add_property(xmlElement, 'Standard', 'True')
                add_property(xmlElement, 'Expert', 'True')
            elif stage_num == 3:
                add_property(xmlElement, 'Standard', 'False')
                add_property(xmlElement, 'Expert', 'True')
    else:
        # Default stage for villain/main_scheme without explicit stage
        type_code = propDict.get('type_code', '')
        if type_code == 'villain':
            add_property(xmlElement, 'Stage', '0')
            add_property(xmlElement, 'Standard', 'True')
            add_property(xmlElement, 'Expert', 'True')
        elif type_code == 'main_scheme':
            add_property(xmlElement, 'Stage', '0')


# ---------------------------------------------------------------------------
# Setup card generation (§3)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 1A Parsing for Villain Setup Cards (§3)
# ---------------------------------------------------------------------------

# Word-to-number mapping for modular count extraction
WORD_TO_NUMBER = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
}

def parse1AText(all_cards, villain_set_code, set_type_map):
    """
    Parse the main_scheme 1A text for a given villain set to extract:
    - nbModular: number of free-choice modular encounter sets required
    - mandatoryModular: dict of mandatory modular set codes and names
    - recommendedModular: dict of recommended modular set codes and names
    Returns (nb_modular, mandatory_modular_str, recommended_modular_str) or (None, None, None).
    """
    # Find the main_scheme 1A card associated with this villain
    scheme_1a = None
    for card in all_cards:
        if (card.get('type_code') == 'main_scheme'
                and card.get('stage') in [1, '1', '1A', 'I']
                and card.get('code', '').endswith('a')):
            # Check if this scheme belongs to the same villain set or its parent set
            card_set = card.get('set_code', '')
            if card_set == villain_set_code:
                scheme_1a = card
                break
    
    if scheme_1a is None:
        return None, None, None
    
    text = scheme_1a.get('text', '')
    if not text:
        return None, None, None
    
    # Strip HTML tags for easier regex parsing
    clean_text = re.sub(r'<[^>]+>', '', text)
    
    # Load name maps for code resolution
    set_name_map = loadSetNameMap()
    octgn_setup_map = loadOctgnSetupMap()
    
    # Build the villain set name for filtering
    # We need the display name of the villain set to ignore it in the encounter sets list
    villain_name = None
    for sets_file in ["sets_fanmade.json", "sets.json"]:
        sets_path = os.path.join("datapack", sets_file)
        if not os.path.exists(sets_path):
            alt_path = os.path.join("c:", os.sep, "github", "marvelsdb_fanmade_data", sets_file)
            if os.path.exists(alt_path):
                sets_path = alt_path
        if os.path.exists(sets_path):
            with open(sets_path, encoding="utf-8") as sf:
                for s in json.load(sf):
                    if s.get("code") == villain_set_code:
                        villain_name = s.get("name", "").lower().strip()
                        break
        if villain_name:
            break
    if villain_name:
        print(f"[1A PARSE] Villain name to ignore: '{villain_name}'")
    
    # --- Extract nbModular ---
    nb_modular = None
    
    # Pattern: "X modular encounter set(s)" or "X modular set(s)"
    # Also handles "X additional selected modular sets"
    patterns = [
        r'(\w+)\s+(?:additional\s+(?:selected\s+)?)?modular\s+(?:encounter\s+)?sets?',
        r'(\d+)\s*[\u2013\u2014-]\s*(\d+)\s+modular\s+sets?',  # "3-4 modular sets"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, clean_text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) == 2 and groups[1]:  # Range like "3-4"
                try:
                    nb_modular = int(groups[1])  # Use upper bound
                except ValueError:
                    pass
            else:
                word = groups[0].lower()
                nb_modular = WORD_TO_NUMBER.get(word)
                if nb_modular is None:
                    try:
                        nb_modular = int(word)
                    except ValueError:
                        pass
            if nb_modular is not None:
                break
    
    # --- Extract mandatoryModular ---
    # Parse the encounter sets sentence: "[Name1], [Name2], and Standard encounter sets."
    # Everything listed that is NOT the villain set, Standard, or Expert = mandatory
    mandatory = {}
    IGNORED_SETS = {'standard', 'expert'}
    
    # Strategy: find all sentences ending with "encounter sets" or "encounter set",
    # filter out the one about "modular encounter set(s)", use the remaining.
    # The target sentence looks like: "Namor, Atlantean Wilds, and Standard encounter sets."
    all_enc_matches = list(re.finditer(
        r'([A-Z][\w\s,\'-]+(?:\s+and\s+[\w\s\'-]+)?)\s+encounter\s+sets?',
        clean_text
    ))
    # Filter out matches containing "modular" 
    non_modular_matches = [m for m in all_enc_matches if 'modular' not in m.group(0).lower()]
    enc_sets_match = non_modular_matches[0] if non_modular_matches else None
    
    if enc_sets_match:
        enc_list_text = enc_sets_match.group(1).strip()
        # Remove parenthetical content like "(Namor (III) instead for expert.)"
        enc_list_text = re.sub(r'\([^)]*\)', '', enc_list_text).strip()
        # Split on ", and " first (higher priority), then ", ", then " and "
        parts = re.split(r',\s+and\s+|,\s+|\s+and\s+', enc_list_text)
        for part in parts:
            part = part.strip().rstrip('.')
            if not part:
                continue
            part_lower = part.lower()
            # Ignore villain set name, Standard, Expert
            if part_lower in IGNORED_SETS:
                continue
            if villain_name and part_lower == villain_name:
                continue
            # This is a mandatory modular set — resolve its code and pile
            resolved_code = _resolve_set_code(part, set_name_map, octgn_setup_map, set_type_map)
            pile_cat, pile_shuffle = _resolve_pile_category(resolved_code, part)
            mandatory[resolved_code] = [part, pile_cat, pile_shuffle]
    
    mandatory_str = str(mandatory) if mandatory else None
    
    # --- Extract recommendedModular ---
    recommended = {}
    
    # Pattern: "(recommended: Name1 and Name2)" or "(recommended: Name)"
    rec_match = re.search(r'\(recommended:?\s*([^)]+)\)', clean_text, re.IGNORECASE)
    if rec_match:
        rec_text = rec_match.group(1).strip().rstrip('.')
        # Split on " and " for multiple recommendations
        rec_names = re.split(r'\s+and\s+', rec_text, flags=re.IGNORECASE)
        for rec_name in rec_names:
            rec_name = rec_name.strip()
            if rec_name:
                resolved_code = _resolve_set_code(rec_name, set_name_map, octgn_setup_map, set_type_map)
                pile_cat, pile_shuffle = _resolve_pile_category(resolved_code, rec_name)
                recommended[resolved_code] = [rec_name, pile_cat, pile_shuffle]
    
    recommended_str = str(recommended) if recommended else None
    
    if nb_modular is not None or mandatory_str is not None or recommended_str is not None:
        print(f"[1A PARSE] {villain_set_code}: nbModular={nb_modular}, mandatory={mandatory_str}, recommended={recommended_str}")
    
    return nb_modular, mandatory_str, recommended_str


def _resolve_set_code(set_name, set_name_map, octgn_setup_map, set_type_map):
    """
    Resolve a set name to its OCTGN code.
    Priority: 1) Fanmade set_name_map exact match, 2) OCTGN official setup map,
    3) Fuzzy match in set_type_map (modular only), 4) Synthetic key.
    """
    name_lower = set_name.lower().strip()
    
    # 1. Exact match in fanmade set name map
    if name_lower in set_name_map:
        return set_name_map[name_lower]
    
    # 2. Exact match in OCTGN official setup map
    if name_lower in octgn_setup_map:
        return octgn_setup_map[name_lower]
    
    # 3. Fuzzy match in set_type_map (for modular sets)
    for code, stype in set_type_map.items():
        if stype == 'modular':
            code_normalized = code.replace('_', ' ').lower()
            if name_lower in code_normalized or code_normalized in name_lower:
                return code
    
    # 4. Fallback: synthetic key
    safe_key = re.sub(r'[^a-z0-9_]', '_', name_lower)
    print(f"[1A PARSE] WARNING: Could not resolve set code for '{set_name}', using synthetic key '{safe_key}'")
    return safe_key


def _resolve_pile_category(set_code, set_name):
    """
    Determine the OCTGN pile category for a set.
    Returns ('Campaign', False) for campaign sets, ('Encounter', False) otherwise.
    Convention from Hunting Season: campaign → 'Campaign' pile, encounter → 'Encounter' pile.
    """
    code_lower = set_code.lower() if set_code else ''
    name_lower = set_name.lower() if set_name else ''
    if 'campaign' in code_lower or 'campaign' in name_lower:
        return 'Campaign', False
    return 'Encounter', False


def generateSetupCards(xmlCards, packInfo):
    """Generate virtual setup cards for all distinct sets in the pack (§3)."""
    base_id = packInfo['octgn_id']
    uuid_base = base_id[:-6] if len(base_id) >= 6 else base_id

    set_type_map = loadSetTypeMap()

    # Collect all distinct set_codes AND all cards from ALL card files
    all_set_codes = []
    all_cards = []
    seen_codes = set()
    for curFile in runFileList:
        if path.exists(curFile):
            with open(curFile, encoding="utf-8") as jf:
                cards = json.load(jf)
                all_cards.extend(cards)
                for card in cards:
                    sc = card.get("set_code", "")
                    if sc and sc not in seen_codes:
                        seen_codes.add(sc)
                        all_set_codes.append(sc)

    # Generate a setup card for each distinct set
    counter = 0
    for sc in all_set_codes:
        set_type = set_type_map.get(sc, "")

        # §8 Override: skip ignored set types
        if shouldIgnoreCard(sc, set_type_map):
            print(f"[OVERRIDES] Skipping setup card for ignored set '{sc}' (type='{set_type}')")
            continue

        setup_type = SETUP_TYPE_MAP.get(set_type)
        if not setup_type:
            # Fallback: guess type from name
            if sc.endswith("_nemesis"):
                setup_type = "fm_encounter_setup"
            else:
                print(f"[SETUP] Skipping unknown set_type for '{sc}' (type='{set_type}')")
                continue

        # Generate UUID (§3)
        if counter == 0:
            suffix = "000000"
        elif counter == 1:
            suffix = "990000"
        else:
            suffix = f"{counter:06d}"
        setup_id = uuid_base + suffix
        counter += 1

        setup_card = ET.SubElement(xmlCards, 'card')
        setup_card.set('id', setup_id)
        setup_card.set('name', sc.lower())
        prop_type = ET.SubElement(setup_card, 'property')
        prop_type.set('name', 'Type')
        prop_type.set('value', setup_type)
        prop_owner = ET.SubElement(setup_card, 'property')
        prop_owner.set('name', 'Owner')
        prop_owner.set('value', sc.lower())

        # §3 Villain Setup — 1A Parsing (with §8 override support)
        if setup_type == 'fm_villain_setup':
            scenario_override = getScenarioOverride(sc)
            if scenario_override:
                # Use explicit values from octgn_overrides.json
                print(f"[OVERRIDES] Using scenario override for '{sc}'")
                ovr_nb = scenario_override.get('nb_modular')
                if ovr_nb is not None:
                    prop_nb = ET.SubElement(setup_card, 'property')
                    prop_nb.set('name', 'nbModular')
                    prop_nb.set('value', str(ovr_nb))
                ovr_mandatory = scenario_override.get('mandatory_modulars')
                if ovr_mandatory:
                    mandatory_str = str(ovr_mandatory)
                    prop_mand = ET.SubElement(setup_card, 'property')
                    prop_mand.set('name', 'mandatoryModular')
                    prop_mand.set('value', mandatory_str)
                ovr_recommended = scenario_override.get('recommended_modulars')
                if ovr_recommended:
                    recommended_str = str(ovr_recommended)
                    prop_rec = ET.SubElement(setup_card, 'property')
                    prop_rec.set('name', 'recommendedModular')
                    prop_rec.set('value', recommended_str)
            else:
                # Default: parse 1A text
                nb_modular, mandatory_str, recommended_str = parse1AText(all_cards, sc, set_type_map)
                if nb_modular is not None:
                    prop_nb = ET.SubElement(setup_card, 'property')
                    prop_nb.set('name', 'nbModular')
                    prop_nb.set('value', str(nb_modular))
                if mandatory_str is not None:
                    prop_mand = ET.SubElement(setup_card, 'property')
                    prop_mand.set('name', 'mandatoryModular')
                    prop_mand.set('value', mandatory_str)
                if recommended_str is not None:
                    prop_rec = ET.SubElement(setup_card, 'property')
                    prop_rec.set('name', 'recommendedModular')
                    prop_rec.set('value', recommended_str)

        print(f"[SETUP] Generated setup card: {sc} -> {setup_type} (id={setup_id})")


# ---------------------------------------------------------------------------
# XML Set creation
# ---------------------------------------------------------------------------

def createXmlCards(fromFile):
    with open(fromFile, encoding="utf-8") as json_file:
        data = json.load(json_file)
        packInfo = getPack(data[0]['pack_code'])
        xmlSet = ET.Element('set')
        xmlSet.set('name', packInfo['name'])
        xmlSet.set('id', packInfo['octgn_id'])
        xmlSet.set('gameId', '055c536f-adba-4bc2-acbf-9aefb9756046')
        xmlSet.set('gameVersion', '0.0.0.0')
        xmlSet.set('version', '1.0.0.0')
        xmlCards = ET.SubElement(xmlSet, 'cards')

        # Ajout du header.xml en premier si HEADER est True
        if HEADER:
            header_path = os.path.join("datapack", "header.xml")
            if os.path.exists(header_path):
                with open(header_path, encoding="utf-8") as header_file:
                    header_content = header_file.read()
                    header_xml = ET.fromstring(header_content)
                    for elem in list(header_xml):
                        xmlCards.insert(0, elem)

        # Auto-generation of setup cards for all distinct sets (§3)
        generateSetupCards(xmlCards, packInfo)

        return xmlSet

def getPackName(fromFile):
    with open(fromFile, encoding="utf-8") as json_file:
        data = json.load(json_file)
        packInfo = getPack(data[0]['pack_code'])
        return packInfo['name']


# ---------------------------------------------------------------------------
# Fill XML set with cards
# ---------------------------------------------------------------------------

ORIGINAL_CARDS_CACHE = {}

def get_original_card(card_code):
    """Retrieve original card properties for duplicate resolution."""
    global ORIGINAL_CARDS_CACHE
    if not ORIGINAL_CARDS_CACHE:
        search_dirs = [
            os.path.join("c:", os.sep, "github", "marvelsdb_fanmade_data", "pack"),
            "datapack"
        ]
        try:
            rel_pack = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "marvelsdb_fanmade_data", "pack"))
            search_dirs.append(rel_pack)
        except Exception:
            pass

        for s_dir in search_dirs:
            if os.path.exists(s_dir):
                for filename in os.listdir(s_dir):
                    if filename.endswith(".json"):
                        filepath = os.path.join(s_dir, filename)
                        try:
                            with open(filepath, encoding="utf-8") as f:
                                cards = json.load(f)
                                if isinstance(cards, list):
                                    for card in cards:
                                        if isinstance(card, dict) and "code" in card:
                                            ORIGINAL_CARDS_CACHE[card["code"]] = card
                        except Exception as e:
                            print(f"[CACHE] Error loading {filepath}: {e}")
        print(f"[CACHE] Loaded {len(ORIGINAL_CARDS_CACHE)} cards into original cache")
    return ORIGINAL_CARDS_CACHE.get(card_code)


def fillXmlSet(xmlSet, fromFile):
    set_type_map = loadSetTypeMap()
    xmlCards = xmlSet.find('cards')
    with open(fromFile, encoding="utf-8") as json_file:
        data = json.load(json_file)
        for i in data:
            # Skip duplicates that do not have their own octgn_id
            if 'duplicate_of' in i and 'octgn_id' not in i:
                continue

            if (i['code'][-1] == 'a' or i['code'][-1].isnumeric()):
                # Resolve and merge properties for duplicate cards
                card_data = i
                if 'duplicate_of' in i:
                    orig_card = get_original_card(i['duplicate_of'])
                    if orig_card:
                        card_data = dict(orig_card)
                        card_data.update(i)
                    else:
                        print(f"[WARNING] duplicate_of '{i['duplicate_of']}' introuvable pour la carte {i['code']} ({i.get('name', '')})")

                # §8 Override: skip ignored set types
                card_set_code = card_data.get('set_code', '')
                if shouldIgnoreCard(card_set_code, set_type_map):
                    continue

                if 'octgn_id' not in card_data:
                    print(f"Carte sans octgn_id ignorée : {card_data.get('name', card_data.get('code', '???'))}")
                    continue

                xmlCard = ET.SubElement(xmlCards, 'card')
                xmlCard.set('name', card_data['name'])
                xmlCard.set('id', card_data['octgn_id'])

                # Card size (§4)
                size = get_card_size(card_data.get('type_code', ''), card_data.get('faction_code', ''))
                if size:
                    xmlCard.set('size', size)

                # Build all properties (§5)
                buildXmlProps(card_data, xmlCard)

                # Alternate faces (§6) — back_link
                if 'back_link' in card_data:
                    alternateCard = findAlt(data, card_data['back_link'])
                    if alternateCard is None:
                        print(f"[WARNING] back_link '{card_data['back_link']}' introuvable pour la carte {card_data['code']} ({card_data['name']}). Alternate ignoree.")
                    else:
                        alt_data = alternateCard
                        if 'duplicate_of' in alternateCard:
                            orig_alt = get_original_card(alternateCard['duplicate_of'])
                            if orig_alt:
                                alt_data = dict(orig_alt)
                                alt_data.update(alternateCard)

                        cardAlternate = ET.SubElement(xmlCard, 'alternate')
                        cardAlternate.set('name', alt_data['name'])
                        cardAlternate.set('type', alt_data['code'][-1])
                        alt_size = get_card_size(alt_data.get('type_code', ''), alt_data.get('faction_code', ''))
                        if alt_size:
                            cardAlternate.set('size', alt_size)
                        buildXmlProps(alt_data, cardAlternate)

                        # Ajoute toutes les cartes c, d, e, f, ... comme alternate
                        code_root = card_data['code'][:-1]
                        for alt_card in data:
                            if 'duplicate_of' in alt_card and 'octgn_id' not in alt_card:
                                continue
                            if alt_card['code'].startswith(code_root) and alt_card['code'][-1] in 'cdefghijklmnopqrstuvwxyz':
                                altx_data = alt_card
                                if 'duplicate_of' in alt_card:
                                    orig_altx = get_original_card(alt_card['duplicate_of'])
                                    if orig_altx:
                                        altx_data = dict(orig_altx)
                                        altx_data.update(alt_card)

                                cardAlternateX = ET.SubElement(xmlCard, 'alternate')
                                cardAlternateX.set('name', altx_data['name'])
                                cardAlternateX.set('type', altx_data['code'][-1])
                                altx_size = get_card_size(altx_data.get('type_code', ''), altx_data.get('faction_code', ''))
                                if altx_size:
                                    cardAlternateX.set('size', altx_size)
                                buildXmlProps(altx_data, cardAlternateX)

                # DISCARDPILE_SETUP handling
                if DISCARDPILE_SETUP:
                    owner_props = [prop for prop in xmlCard.findall('property') if prop.get('name') == 'Owner']
                    if owner_props and owner_props[0].get('value') == DISCARDPILE_SETUP:
                        default_discard = ET.SubElement(xmlCard, 'property')
                        default_discard.set('name', 'DefaultDiscardPile')
                        default_discard.set('value', 'Special Discard')


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

def has_cards(filepath):
    if not path.exists(filepath):
        return False
    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
            return bool(data)
    except Exception:
        return False

valid_files = [f for f in runFileList if has_cards(f)]

# Load all cards for crossover/alternate lookups across files
load_all_pack_cards()

for curFile in valid_files:
    if xmlSet is None:
        xmlSet = createXmlCards(curFile)
    fillXmlSet(xmlSet, curFile)

if packName is None:
    if valid_files:
        packName = getPackName(valid_files[0])
    else:
        raise FileNotFoundError("Aucun fichier de pack contenant des cartes n'a été trouvé.")

# Création du dossier de sortie si besoin
output_dir = f"C:/Github/OCTGN-Marvel-Champions/055c536f-adba-4bc2-acbf-9aefb9756046/Sets/{PACK_CODE}"
os.makedirs(output_dir, exist_ok=True)

# Création du fichier XML
mydata = ET.tostring(xmlSet, pretty_print=True, encoding='utf-8', xml_declaration=True, standalone="yes")

modified_str = mydata.decode('utf-8')
modified_str = modified_str.replace('\u00e2\u0086\u0092', '\u2192')
modified_str = modified_str.replace('\u00e2\u0080\u0094', '\u2014')
mydata = modified_str.encode('utf-8')

with open(f"{output_dir}/set.xml", "wb") as myfile:
    myfile.write(mydata)

print(f"[OK] Generated {output_dir}/set.xml")
