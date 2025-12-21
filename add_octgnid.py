import os
from os import path
import json
import uuid

runFile = 'skrull_menace_by_kajislav'
print(f'fm_{runFile}')  # Doit afficher fm_mystique_by_merlin
pack_code = 'skrull_menace_by_kajislav'

runFileList = [
    os.path.join("datapack", runFile + ".json"),
    os.path.join("datapack", runFile + "_encounter.json")
]
print("runFileList:", runFileList)  # TRACE: affiche la liste des fichiers traités

pack_path = os.path.join("datapack", f"{pack_code}_packs.json")
with open(pack_path) as json_file:
    pack_data = json.load(json_file)
    updated_data = pack_data.copy()
    for item in updated_data:
        if item['code'] == pack_code:
            try:
                if 'octgn_id' not in item.keys():
                    item['octgn_id'] = str(uuid.uuid4())
                    pack_octgn_id = str(item['octgn_id'])[0:30]
                    pack_id = str('00' + str(item['cgdb_id']))[-3:]
                else:
                    pack_octgn_id = str(item['octgn_id'])[0:30]
                    pack_id = str('00' + str(item['cgdb_id']))[-3:]
            except KeyError:
                print("An exception occurred: " + item['code'])

with open(pack_path, 'w') as outfile:
    json.dump(updated_data, outfile, indent='\t', sort_keys=True)

for curFile in runFileList:
    if path.exists(curFile):
        with open(curFile) as json_file:
            data = json.load(json_file)
            updated_data = data.copy()
            for item in updated_data:
                try:
                    if 'duplicate_of' not in item.keys():
                        item['octgn_id'] = pack_octgn_id + pack_id + str('00' + str(item['position']))[-3:]
                except KeyError:
                    print("An exception occurred: " + item['name'])

            for item in updated_data:
                try:
                    if len(item['code']) > 5 and str(item['code'])[4:5] != 'a':
                        for items in updated_data:
                            if items['code'] == str(item['code'])[0:5] + 'a':
                                item['octgn_id'] = items['octgn_id']
                except KeyError:
                    print("An exception occurred: " + item['name'])


        with open(curFile, 'w') as outfile:
            json.dump(updated_data, outfile, indent=4, sort_keys=True)
        
