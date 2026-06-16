import os
import json
import re
import sys
from PIL import Image

generate_png = True
if "--no-png" in sys.argv:
    generate_png = False
    print("Désactivation de la génération des images de setup PNG.")

# ── Configuration ──
JPEG_QUALITY = 60   # Compression quality for OCTGN images (1-100)

# Chemins à adapter si besoin
json_path = "database_images.json"
images_src_dir = "mcdb_images"
sets_base_dir = r"octgn_images\055c536f-adba-4bc2-acbf-9aefb9756046\Sets"
output_file = "output.json"

# Affiche le nombre d'images dans le répertoire source
src_images = [f for f in os.listdir(images_src_dir) if f.lower().endswith(('.jpg', '.png'))]
print(f"Nombre d'images dans le répertoire source '{images_src_dir}': {len(src_images)}")

# Charger les données JSON
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Vider le répertoire sets_base_dir avant de commencer
if os.path.exists(sets_base_dir):
    for root, dirs, files in os.walk(sets_base_dir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))

# Créer les sous-répertoires pour chaque pack_octgn_id
pack_ids = set(card["pack_octgn_id"] for card in data)
for pack_id in pack_ids:
    print(f"[TRACE DOSSIER] pack_id={pack_id} (type={type(pack_id)})")
    pack_dir = os.path.join(sets_base_dir, str(pack_id), "Cards")
    os.makedirs(pack_dir, exist_ok=True)

cards = []  # Liste pour stocker les cartes traitées

# Copier, compresser et renommer les images
for card in data:
    card_id = card["card_id"]
    octgn_id = card["octgn_id"]
    pack_id = card.get("pack_octgn_id")

    #print(f"[TRACE] card_id={card_id}, octgn_id={octgn_id}, pack_octgn_id={pack_id}")

    # Ignore les cartes dont l'octgn_id est vide ou égal à "0"
    if not octgn_id or octgn_id == "0":
        continue

    # Trace si pack_octgn_id est vide ou absent
    if not pack_id:
        print(f"[AVERTISSEMENT] Image ignorée : card_id={card_id} (octgn_id={octgn_id}) n'a pas de pack_octgn_id.")
        continue

    # Chercher l'image source (jpg, png ou webp) : le nom d'origine est card_id (ex: 14001a.jpg)
    src_jpg = os.path.join(images_src_dir, f"{card_id}.jpg")
    src_png = os.path.join(images_src_dir, f"{card_id}.png")
    src_webp = os.path.join(images_src_dir, f"{card_id}.webp")
    if os.path.exists(src_jpg):
        src_img = src_jpg
    elif os.path.exists(src_png):
        src_img = src_png
    elif os.path.exists(src_webp):
        src_img = src_webp
    else:
        continue

    # Output is always .jpg (compressed)
    ext = ".jpg"

    # Le nom cible : si card_id se termine par une lettre, ajouter ".<lettre>" avant l'extension
    # Exception : si card_id finit par "a", retirer le "a" et ne pas ajouter de point
    if card_id.endswith("a"):
        new_name = f"{octgn_id}{ext}"
    elif re.match(r"^(.*?)([a-zA-Z])$", card_id):
        match = re.match(r"^(.*?)([a-zA-Z])$", card_id)
        new_name = f"{octgn_id}.{match.group(2)}{ext}"
    else:
        new_name = f"{octgn_id}{ext}"

    dest_dir = os.path.join(sets_base_dir, pack_id, "Cards")
    dest_img = os.path.join(dest_dir, new_name)

    # Compress image to JPEG at configured quality
    img = Image.open(src_img)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(dest_img, "JPEG", quality=JPEG_QUALITY, optimize=True)
    print(f"Compressé {src_img} -> {dest_img} (qualité {JPEG_QUALITY}%)")

    cards.append(card)  # Ajouter la carte à la liste des cartes traitées

# --- Génération des images de cartes de setup en format PNG ---
if generate_png:
    print("Génération des images pour les cartes de setup (PNG)...")
    import xml.etree.ElementTree as ET

    xml_sets_dir = os.path.join("055c536f-adba-4bc2-acbf-9aefb9756046", "Sets")

    if os.path.exists(xml_sets_dir):
        for set_folder in os.listdir(xml_sets_dir):
            set_xml_path = os.path.join(xml_sets_dir, set_folder, "set.xml")
            if os.path.exists(set_xml_path):
                try:
                    tree = ET.parse(set_xml_path)
                    root = tree.getroot()
                    set_id = root.attrib.get("id")
                    if not set_id:
                        continue

                    cards_element = root.find("cards")
                    if cards_element is None:
                        continue

                    all_cards = list(cards_element.findall("card"))
                    
                    setup_cards = []
                    normal_cards = []
                    for card_el in all_cards:
                        card_id = card_el.attrib.get("id")
                        card_name = card_el.attrib.get("name")
                        
                        props = {}
                        for prop in card_el.findall("property"):
                            p_name = prop.attrib.get("name")
                            p_val = prop.attrib.get("value")
                            if p_name:
                                props[p_name] = p_val
                        
                        card_type = props.get("Type", "")
                        card_owner = props.get("Owner", "")
                        card_number = props.get("CardNumber", "")
                        
                        card_info = {
                            "id": card_id,
                            "name": card_name,
                            "type": card_type,
                            "owner": card_owner,
                            "card_number": card_number
                        }
                        
                        if card_type.endswith("_setup") or card_type in ("fm_villain_setup", "fm_encounter_setup", "fm_hero_setup"):
                            setup_cards.append(card_info)
                        else:
                            normal_cards.append(card_info)

                    for setup_card in setup_cards:
                        owner = setup_card["owner"]
                        setup_id = setup_card["id"]
                        
                        rep_card = None
                        for nc in normal_cards:
                            if nc["owner"] == owner:
                                rep_card = nc
                                break
                        
                        if not rep_card:
                            print(f"[SETUP IMAGE] Aucun représentant trouvé pour {setup_card['name']} (owner={owner})")
                            continue
                        
                        rep_card_number = rep_card["card_number"]
                        if not rep_card_number:
                            continue

                        src_img = None
                        for ext_opt in [".jpg", ".png", ".webp"]:
                            test_path = os.path.join(images_src_dir, f"{rep_card_number}{ext_opt}")
                            if os.path.exists(test_path):
                                src_img = test_path
                                break
                        
                        if not src_img:
                            print(f"[SETUP IMAGE] Image source introuvable pour le représentant {rep_card_number}")
                            continue
                        
                        dest_dir = os.path.join(sets_base_dir, str(set_id), "Cards")
                        os.makedirs(dest_dir, exist_ok=True)
                        dest_path = os.path.join(dest_dir, f"{setup_id}.png")
                        
                        try:
                            img = Image.open(src_img)
                            img.save(dest_path, "PNG")
                            print(f"[SETUP IMAGE] Créé {dest_path} depuis {src_img}")
                        except Exception as ex:
                            print(f"[SETUP IMAGE] Erreur lors de l'enregistrement de {dest_path} : {ex}")
                except Exception as ex:
                    print(f"[SETUP IMAGE] Erreur de parsing du fichier XML {set_xml_path} : {ex}")
else:
    print("Génération des PNG setup désactivée.")


print("Nombre de cartes copiées :", len(cards))

with open(output_file, "w", encoding="utf-8") as outfile:
    json.dump(cards, outfile, ensure_ascii=False, indent=2)

print("Import Terminé.")

# Supprimer les répertoires vides dans sets_base_dir à la fin
for root, dirs, files in os.walk(sets_base_dir, topdown=False):
    for name in dirs:
        dir_path = os.path.join(root, name)
        if not os.listdir(dir_path):
            os.rmdir(dir_path)

print("Nettoyage terminé.")