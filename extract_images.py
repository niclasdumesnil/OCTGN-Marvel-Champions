import os
import glob
import json
import zipfile
import re
from PIL import Image
import io

def main():
    mapping_path = r"c:\github\OCTGN-Marvel-Champions\database_images.json"
    source_dir = r"E:\OCTGN_Image_pack_FR"
    dest_dir = r"E:\OCTGN_image_FR"

    print("Starting extraction and conversion...")
    
    # ensure dest_dir exists
    os.makedirs(dest_dir, exist_ok=True)
    # prepare log file for unmapped entries (overwrite each run)
    log_path = os.path.join(dest_dir, "log.txt")
    try:
        with open(log_path, "w", encoding="utf-8") as _:
            pass
    except Exception:
        print(f"Warning: cannot create log file at {log_path}")

    # 1. Load mapping
    print(f"Loading mapping from {mapping_path}")
    try:
        with open(mapping_path, "r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception as e:
        print(f"Error loading mapping: {e}")
        return

    # build mapping octgn_id -> card_id
    mapping = {}
    for entry in db:
        octgn_id = entry.get("octgn_id")
        card_id = entry.get("card_id")
        if octgn_id and card_id:
            mapping[octgn_id] = card_id

    print(f"Loaded {len(mapping)} mappings.")

    # 2. find .o8c files
    if not os.path.exists(source_dir):
        print(f"Source directory not found: {source_dir}")
        return
        
    o8c_files = glob.glob(os.path.join(source_dir, "*.o8c"))
    print(f"Found {len(o8c_files)} .o8c files in {source_dir}")

    # 3. process each archive
    extracted_count = 0
    for o8c in o8c_files:
        print(f"Processing archive: {os.path.basename(o8c)}")
        try:
            with zipfile.ZipFile(o8c, "r") as z:
                # Collect image entries and group by base name (handle XXX, XXX.a, XXX.b -> same base)
                image_infos = [fi for fi in z.infolist() if not fi.is_dir() and os.path.splitext(fi.filename)[1].lower() in ('.png', '.jpg', '.jpeg')]

                groups = {}
                for fi in image_infos:
                    basename = os.path.basename(fi.filename)
                    name, ext = os.path.splitext(basename)
                    m = re.match(r'^(?P<base>.+)\.([a-zA-Z])$', name)
                    if m:
                        base = m.group('base')
                        suffix = m.group(2).lower()
                    else:
                        base = name
                        suffix = ''
                    groups.setdefault(base, []).append((fi, name, suffix))

                # Process each group: if multiple variants exist for same base, generate unique card ids YYYYa/YYYb/YYYc
                for base, entries in groups.items():
                    # sort entries: no-suffix first, then alphabetical by suffix
                    entries.sort(key=lambda t: (0 if t[2] == '' else (ord(t[2]) - ord('a') + 1)))

                    # Resolve initial mapping for each entry using same priority as before
                    resolved = []  # list of mapped card_id or None
                    for fi, name, suffix in entries:
                        octgn_id = name
                        m2 = re.match(r'^(?P<base>.+)\.([a-zA-Z])$', name)
                        if m2:
                            b = m2.group('base')
                            letter = m2.group(2).lower()
                            candidate = f"{b}{letter}"
                            if candidate in mapping:
                                octgn_id = candidate
                            elif b in mapping:
                                octgn_id = b
                            elif f"{b}a" in mapping:
                                octgn_id = f"{b}a"
                        resolved.append(mapping.get(octgn_id))

                    # Determine base card id set (strip trailing letter if present)
                    base_cards = set()
                    for mc in resolved:
                        if mc:
                            if len(mc) > 1 and mc[-1].isalpha():
                                base_cards.add(mc[:-1])
                            else:
                                base_cards.add(mc)

                    if len(entries) > 1 and len(base_cards) == 1:
                        # Multiple variants mapping to the same base -> assign a,b,c ... to outputs
                        base_card = next(iter(base_cards))
                        for idx, (fi, name, suffix) in enumerate(entries):
                            mapped_mc = resolved[idx]
                            if not mapped_mc:
                                try:
                                    with open(log_path, "a", encoding="utf-8") as logf:
                                        logf.write(f"{os.path.basename(o8c)},{fi.filename},{name}\n")
                                except Exception:
                                    pass
                                print(f"No mapping for {fi.filename}; skipping (logged)")
                                continue
                            letter = chr(ord('a') + idx)
                            target_card = f"{base_card}{letter}"
                            dest_path = os.path.join(dest_dir, f"{target_card}.webp")
                            try:
                                with z.open(fi) as f:
                                    img_data = f.read()
                                img = Image.open(io.BytesIO(img_data))
                                img.load()
                                if img.mode not in ("RGB", "RGBA"):
                                    img = img.convert("RGBA")
                                img.save(dest_path, "WEBP")
                                extracted_count += 1
                            except Exception as e:
                                print(f"Error converting {fi.filename} from {os.path.basename(o8c)}: {e}")
                    else:
                        # No special grouping needed; write each mapped file to its mapped card_id
                        for idx, (fi, name, suffix) in enumerate(entries):
                            mapped_mc = resolved[idx]
                            if not mapped_mc:
                                try:
                                    with open(log_path, "a", encoding="utf-8") as logf:
                                        logf.write(f"{os.path.basename(o8c)},{fi.filename},{name}\n")
                                except Exception:
                                    pass
                                print(f"No mapping for {fi.filename}; skipping (logged)")
                                continue
                            dest_path = os.path.join(dest_dir, f"{mapped_mc}.webp")
                            try:
                                with z.open(fi) as f:
                                    img_data = f.read()
                                img = Image.open(io.BytesIO(img_data))
                                img.load()
                                if img.mode not in ("RGB", "RGBA"):
                                    img = img.convert("RGBA")
                                img.save(dest_path, "WEBP")
                                extracted_count += 1
                            except Exception as e:
                                print(f"Error converting {fi.filename} from {os.path.basename(o8c)}: {e}")
        except Exception as e:
            print(f"Error reading zip {o8c}: {e}")

    print(f"Successfully extracted and converted {extracted_count} images.")

if __name__ == "__main__":
    main()
