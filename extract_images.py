import os
import glob
import json
import zipfile
from PIL import Image
import io

def main():
    mapping_path = r"c:\github\OCTGN-Marvel-Champions\database_images.json"
    source_dir = r"C:\Users\nicol\Downloads\OCTGN_Image_pack_FR"
    dest_dir = r"C:\Users\nicol\Downloads\FR"

    print("Starting extraction and conversion...")
    
    # ensure dest_dir exists
    os.makedirs(dest_dir, exist_ok=True)

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
                for file_info in z.infolist():
                    filename = file_info.filename
                    if file_info.is_dir():
                        continue
                    
                    basename = os.path.basename(filename)
                    name, ext = os.path.splitext(basename)
                    ext = ext.lower()
                    
                    if ext in [".png", ".jpg", ".jpeg"]:
                        octgn_id = name
                        if octgn_id in mapping:
                            card_id = mapping[octgn_id]
                            dest_path = os.path.join(dest_dir, f"{card_id}.webp")
                            
                            try:
                                with z.open(file_info) as f:
                                    img_data = f.read()
                                
                                img = Image.open(io.BytesIO(img_data))
                                img.save(dest_path, "WEBP")
                                extracted_count += 1
                            except Exception as e:
                                print(f"Error converting {filename} from {os.path.basename(o8c)}: {e}")
        except Exception as e:
            print(f"Error reading zip {o8c}: {e}")

    print(f"Successfully extracted and converted {extracted_count} images.")

if __name__ == "__main__":
    main()
