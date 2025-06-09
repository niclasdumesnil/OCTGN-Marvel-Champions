import os
import json
import shutil
import re

# Chemins à adapter si besoin
json_path = "database_images.json"
images_src_dir = "mcdb_images"
sets_base_dir = r"octgn_images\055c536f-adba-4bc2-acbf-9aefb9756046\Sets"

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
    pack_dir = os.path.join(sets_base_dir, pack_id, "Cards")  # Ajoute le sous-répertoire "cards"
    os.makedirs(pack_dir, exist_ok=True)

# Copier et renommer les images
for card in data:
    card_id = card["card_id"]
    octgn_id = card["octgn_id"]
    pack_id = card["pack_octgn_id"]

    # Ignore les cartes dont l'octgn_id est vide ou égal à "0"
    if not octgn_id or octgn_id == "0":
        continue

    # Chercher l'image source (jpg ou png), en ajoutant un "." avant la lettre finale de card_id si besoin
    match = re.match(r"^(.*?)([a-zA-Z])$", card_id)
    if match:
        card_id_filename = f"{match.group(1)}.{match.group(2)}"
    else:
        card_id_filename = card_id

    src_jpg = os.path.join(images_src_dir, f"{card_id_filename}.jpg")
    src_png = os.path.join(images_src_dir, f"{card_id_filename}.png")
    if os.path.exists(src_jpg):
        src_img = src_jpg
        ext = ".jpg"
    elif os.path.exists(src_png):
        src_img = src_png
        ext = ".png"
    else:
        continue

    # Le nom cible est toujours octgn_id + extension
    new_name = f"{octgn_id}{ext}"

    dest_dir = os.path.join(sets_base_dir, pack_id, "Cards")
    dest_img = os.path.join(dest_dir, new_name)

    shutil.copy2(src_img, dest_img)
    print(f"Copié {src_img} -> {dest_img}")

print("Import Terminé.")

# Supprimer les répertoires vides dans sets_base_dir à la fin
for root, dirs, files in os.walk(sets_base_dir, topdown=False):
    for name in dirs:
        dir_path = os.path.join(root, name)
        if not os.listdir(dir_path):
            os.rmdir(dir_path)

print("Nettoyage terminé.")