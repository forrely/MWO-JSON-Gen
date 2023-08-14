from email.policy import default
import os
import shutil
from tkinter import E
import zipfile
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
#from lxml import lET
import re

gamePath = "F:\Program Files (x86)\SteamLibrary\steamapps\common\MechWarrior Online"
Weapons  = {}

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
		inheritId = wElement.get("InheritFrom")
		#t_ =  wElement.find("WeaponStats").get("type") if inheritId == None else 
			
		weapons[wElement.get("name")] = {
			"id": wElement.get("id"),
			"HardpointAliases": wElement.get("HardpointAliases").split(","),
			"type": wElement.find("WeaponStats").get("type") if inheritId is None else "",
			"inheritId": inheritId
		}
	
	#propagate inherited stats
	for w in weapons.values():
		if w["inheritId"] is not None:
			for parent_w in weapons.values():
				if parent_w["id"] == w["inheritId"]:
					w["type"] = parent_w["type"]

	
	print("writing json:\n")
	with open('Weapons.json', 'w') as f:
		json.dump(weapons, f, indent=4, separators=(", ", " = "), sort_keys=True)					
		#destination_dir = os.path.join(source_dir, mech_name)
	
	global Weapons
	Weapons = weapons





def read_and_convert_mechpaks(mech_dir):
	print("reading...")
	print("The source directory is:", mech_dir)

	data = {
		"mechs": defaultdict(dict)
	}

	mechs = defaultdict(dict)
	
	# Create list of hardpoint aliases to determine component hardpoint list
	HardpointTypeAliases = defaultdict(dict)
	for w in Weapons.values():
		if w["type"] in HardpointTypeAliases:
			HardpointTypeAliases[w["type"]].update(w["HardpointAliases"]) 
		else:
			HardpointTypeAliases[w["type"]] = set(w["HardpointAliases"])
	for ht in HardpointTypeAliases:
		HardpointTypeAliases[ht].update([ht])

	for file in os.listdir(mech_dir):
		if file.endswith(".pak"):
			mech_name = os.path.basename(file[:-4])
			

			if mech_name[0] == 'a':
				print("Found a zipped file:", mech_name)
				data["mechs"][mech_name] = { "Variants": {}}
				with zipfile.ZipFile(os.path.join(mech_dir, file), "r") as zip_ref:
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
							for s in root.iter("Set"):
								setName = s.get("name")
								omniComponents[setName]["SetBonuses"] = defaultdict(dict)
								#print("testing: ")
								#print(data["mechs"][mech_name])
								#print(setName.upper())
								#for v in data["mechs"][mech_name]["variants"]:
									#print(setName.upper() == v)
								data["mechs"][mech_name]["Variants"][setName.upper()]["SetBonuses"] = defaultdict(dict)
								for setBonus in s.iter("Bonus"):
									count = setBonus.get("PieceCount")
									quirks = {}
									for q in setBonus.iter('Quirk'):
										if q.get("name").find("rear") == -1:
											quirks[q.get("name")] = float(q.get("value"))
									#omniComponents[setName]["SetBonuses"][count] = quirks
									data["mechs"][mech_name]["Variants"][setName.upper()]["SetBonuses"][count] = quirks

								for component in s.iter("component"):
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


							def get_weapon_type(testingNames):
								
								for t in HardpointTypeAliases:
									if any(n in testingNames for n in HardpointTypeAliases[t]):
										return t
								print("error: hardpoint not found\n", testingNames, "\n-\n", HardpointTypeAliases)
								return ""

							hardpointIndex = defaultdict(dict)
							for hardpoint in root.iter("Hardpoint"):
								for w in hardpoint.iter("WeaponSlot"):
									names = []
									for a in w.iter("Attachment"):
										names.append(a.get("search"))
									t = get_weapon_type(names) #get_weapon_type(attachment.get("search") for attachment in w)
									if t in hardpointIndex:
										hardpointIndex[int(hardpoint.get("id"))][t] += 1
									else:
										hardpointIndex[int(hardpoint.get("id"))][t] = 1
							#data["mechs"][mech_name]


							for variant in data["mechs"][mech_name]["Variants"].values():
								for component in variant["ComponentList"].values():
									componentHardpoints = defaultdict(dict)
									for hid in component["HardpointIds"]:
										if hid not in hardpointIndex:
											print("error: hardpoint not found in index: "+str(hid)+" for "+mechvariant)
											continue
										for hptype in hardpointIndex[hid]:

										#hinfo = hardpointIndex[hid]
											if  hptype in componentHardpoints:
												componentHardpoints[hptype] += hardpointIndex[hid][hptype]
											else:
												componentHardpoints[hptype] = hardpointIndex[hid][hptype]
									component["Hardpoints"] = componentHardpoints

							


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
	#source_dir = os.getcwd()
  	#copy_mdf_and_xml_files(source_dir)
	read_and_convert_weapons(os.path.join(gamePath, "Game\GameData\Libs\Items\Weapons\Weapons.xml"))
	read_and_convert_mechpaks(os.path.join(gamePath, "Game\mechs"))