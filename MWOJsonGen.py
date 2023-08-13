import os
import shutil
from tkinter import E
import zipfile
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
#from lxml import lET
import re

class CommentedTreeBuilder(ET.TreeBuilder):
    def comment(self, data):
        self.start(ET.Comment, {})
        self.data(data)
        self.end(ET.Comment)

def copy_mdf_and_xml_files(source_dir):
	print("The source directory is:", source_dir)
	for file in os.listdir(source_dir):
		if file.endswith(".pak"):
			zip_file_name = os.path.basename(file[:-4])

		print("Found a zipped file:", zip_file_name)
		destination_dir = os.path.join(source_dir, zip_file_name)

		print("Creating destination directory:", destination_dir)
		if not os.path.exists(destination_dir):
			os.mkdir(destination_dir)

		with zipfile.ZipFile(os.path.join(source_dir, file), "r") as zip_ref:
			for member in zip_ref.namelist():
				if member.endswith(".mdf") or member.endswith(".xml"):
					print("Extracting file:", member)
					filename = os.path.basename(member)
					if not filename:
						continue
					source = zip_ref.open(member)
					target = open(os.path.join(destination_dir, filename), "wb")
					with source, target:
						shutil.copyfileobj(source, target)

def read_and_convert_weapons(weapon_path):
	print("reading weapons: ", weapon_path)
	file = open(weapon_path, "r")
	tree = ET.parse(file)
	root = tree.getroot()

	weapons = {} #defaultdict(dict)
	for wElement in root.iter("Weapon"):
		weapons[wElement.get("name")] = {
			"id": wElement.get("id"),
			"HardpointAliases": wElement.get("HardpointAliases").split(","),
			"type": wElement.find("WeaponStats").get("type")
		}
	
	print("writing json:\n")
	with open('Weapons.json', 'w') as f:
		json.dump(weapons, f, indent=4, separators=(", ", " = "), sort_keys=True)					
		#destination_dir = os.path.join(source_dir, mech_name)


def read_and_convert_mechpaks(mech_dir):
	print("reading...")
	print("The source directory is:", mech_dir)

	data = {
		"mechs": defaultdict(dict)
	}

	mechs = defaultdict(dict)
	

	for file in os.listdir(mech_dir):
		if file.endswith(".pak"):
			mech_name = os.path.basename(file[:-4])
			

			if mech_name[0] == 'a':
				print("Found a zipped file:", mech_name)
				data["mechs"][mech_name] = { "Variants": {}}
				with zipfile.ZipFile(os.path.join(source_dir, file), "r") as zip_ref:
					for member in zip_ref.namelist():
						if member.endswith(".mdf"):
							mechvariant = os.path.basename(member)
							openedFile = zip_ref.open(member)

							variant = {
								# "Name": "",
								# "MaxTons": 0,
								# "BaseTons": 0,
								# "MaxJumpJets": 0,
								# "MinEngineRating": 0,
								# "MaxEngineRating": 0,
								# "Components": {},
								# "MovementTuningConfiguration": {},
								# "QuirkList": {}
							}
							#if mech_name not in mechs:
									#mechs[mech_name]
							tree = ET.parse(openedFile)
							#print(tree)
							root = tree.getroot()
							baseStats = root.find("Mech").attrib
							#print(baseStats)
							components = {}
							for c in root.iter("Component"):
								components[c.get("Name")] = {}
								components[c.get("Name")]["HardpointIds"] = []
								for h in c.iter("Hardpoint"):
									components[c.get("Name")]["HardpointIds"].append(int(h.get("ID")))
								#also get internal and fixed items (and slots?)
							#print(components)
							quirks = {}
							for q in root.iter('Quirk'):
								if q.get("name").find("rear") == -1:
									quirks[q.get("name")] = float(q.get("value"))

							#print(quirks)

							#for child in root:
							#	mechs[mech_name]["variants"][mechvariant][child.tag] = child.attrib
							variant["Mech"] = baseStats
							variant["ComponentList"] = components
							variant["QuirkList"] = quirks
							if baseStats["Variant"] == "ANH-1A":
								print(variant)
							data["mechs"][mech_name]["Variants"][baseStats["Variant"].upper()] = variant
		
					for member in zip_ref.namelist():
						if os.path.basename(member).find("omnipods") >= 0:
							openedFile = zip_ref.open(member)
							tree = ET.parse(openedFile)
							root = tree.getroot()

							omniComponents = defaultdict(dict)							
							for set in root.iter("Set"):
								setName = set.get("name")
								omniComponents[setName]["SetBonuses"] = defaultdict(dict)
								#print("testing: ")
								#print(data["mechs"][mech_name])
								#print(setName.upper())
								#for v in data["mechs"][mech_name]["variants"]:
									#print(setName.upper() == v)
								data["mechs"][mech_name]["Variants"][setName.upper()]["SetBonuses"] = defaultdict(dict)
								for setBonus in set.iter("Bonus"):
									count = setBonus.get("PieceCount")
									quirks = {}
									for q in setBonus.iter('Quirk'):
										if q.get("name").find("rear") == -1:
											quirks[q.get("name")] = float(q.get("value"))
									#omniComponents[setName]["SetBonuses"][count] = quirks
									data["mechs"][mech_name]["Variants"][setName.upper()]["SetBonuses"][count] = quirks

								for component in set.iter("component"):
									quirks = {}
									hardpointIds = []
									for q in component.iter('Quirk'):
										quirks[q.get("name")] = float(q.get("value"))
									for h in component.iter("Hardpoint"):
										hardpointIds.append(int(h.get("ID")))

									data["mechs"][mech_name]["Variants"][setName.upper()]["ComponentList"][component.get("name")]["QuirkList"] = quirks
									data["mechs"][mech_name]["Variants"][setName.upper()]["ComponentList"][component.get("name")]["HardpointIds"] = hardpointIds
									
								
							#data["mechs"][mech_name]["OmniPods"] = omniComponents
						
						if os.path.basename(member).find("hardpoints") >= 0:
							openedFile = zip_ref.open(member)
							tree = ET.parse(openedFile)
							root = tree.getroot()


							def get_weapon_type(names):
								energyAliases = ["Missile20"]
								if any(n in names for e in energyAliases):
									return "Energy"
							hardpointIndex = {}
							for hardpoint in root.iter("Hardpoint"):
								for w in hardpoint.iter("WeaponSlot"):
									get_weapon_type(attachment.get("search") for attachment in w)

							# matches = re.findall(
							# 	r"<Hardpoint id=\"(\d+)\">[\s\n\t]*<!--(left arm|right arm|left leg|right leg|left torso|right torso|centre torso|head), (\d+)? ?(Ballistic|Missile|Energy|AMS)-->",
							# 	openedFile.read().decode('utf-8'),
							# 	re.IGNORECASE
							# 	)
							
							# print(matches)
							# hardpointIndex = {}
							# for m in matches:
							# 	hardpointIndex[int(m[0])] = {
							# 		"part": m[1],
							# 		"amount": 1 if m[2]=="" else int(m[2]),
							# 		"type": m[3]}
							
							#data["mechs"][mech_name]["Hardpoints"] = hardpoints

							for variant in data["mechs"][mech_name]["Variants"].values():
								for component in variant["ComponentList"].values():
									cHardpoints = {}
									for hid in component["HardpointIds"]:
										if hid not in hardpointIndex:
											print("error: hardpoint not found in index: "+str(hid)+" for "+mechvariant)
											continue
										hinfo = hardpointIndex[hid]
										if hinfo["type"] in cHardpoints:
											cHardpoints[hinfo["type"]] += hinfo["amount"]
										else:
											cHardpoints[hinfo["type"]] = hinfo["amount"]
									component["Hardpoints"] = cHardpoints

							


							# tree = ET.parse(openedFile)#, ET.XMLParser(target=CommentedTreeBuilder()))
							# root = tree.getroot()

							# hardpoints = defaultdict(dict)							
							# for h in root.iter("Hardpoint"):
							# 	continue
								#hardpoints[int(h.get("id"))] = 




	
	#print(data)				
	print("writing json:\n")
	with open('Mechs.json', 'w') as f:
		json.dump(data, f, indent=4, separators=(", ", " = "), sort_keys=True)					
		#destination_dir = os.path.join(source_dir, mech_name)

if __name__ == "__main__":
	source_dir = os.getcwd()
  	#copy_mdf_and_xml_files(source_dir)
	read_and_convert_mechpaks(source_dir)