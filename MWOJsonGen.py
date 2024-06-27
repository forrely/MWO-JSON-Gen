import os
import shutil
import zipfile
import json
import xml.etree.ElementTree as ET
from collections import defaultdict

gamePath = r"G:\Program Files (x86)\Steam\steamapps\common\MechWarrior Online"

GameVersion = "unknown"
Weapons = {}
MechIDs = {}
OmnipodIDs = {}


# For reference:
# Weapon data "Game\GameData\Libs\Items\Weapons\Weapons.xml"
# Shots per ammo "Game\GameData\Libs\Items\Modules\Ammo.xml"
# Mech data "Game\GameData\Libs\Items\Mechs\Mechs.xml"
# Omnipods r"Game\GameData\Libs\Items\OmniPods.xml"
# Mechs and their quirks "Game\mechs"

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

def weapon_xml_element_to_json(wElement):
	inheritId = wElement.get("InheritFrom")
	weapon = {
		"id": wElement.get("id"),
		"HardpointAliases": wElement.get("HardpointAliases").split(","),
		"type": wElement.find("WeaponStats").get("type") if inheritId is None else "",
		"inheritId": inheritId,
		"faction": wElement.get("faction"),
		"WeaponStats": wElement.attrib
	}
	return weapon

def read_and_convert_weapons(weapon_path):
	print("reading weapons: ", weapon_path)
	file = open(weapon_path, "r")
	tree = ET.parse(file)
	root = tree.getroot()

	weapons = {
		"_GameVersion": GameVersion,
		"weapons": {}
		} 
	for wElement in root.iter("Weapon"):
		inheritFrom = wElement.get("InheritFrom") 
		weapons["weapons"][wElement.get("name")] = wElement.attrib	
		
		weapons["weapons"][wElement.get("name")].update({
			"HardpointAliases": wElement.get("HardpointAliases").split(","),
			"WeaponStats": wElement.find("WeaponStats").attrib if inheritFrom is None else None,
			"Loc": wElement.find("Loc").attrib
		})
	
	#propagate inherited stats
	for w in weapons["weapons"].values():
		if "InheritFrom" in w and w["InheritFrom"] is not None:
			for parent_w in weapons["weapons"].values():
				if parent_w["id"] == w["InheritFrom"]:
					#w["type"] = parent_w["type"]
					w["WeaponStats"] = parent_w["WeaponStats"]
	
	for w in weapons["weapons"].values():
		if "ammoType" in w["WeaponStats"]:
			w["WeaponStats"]["ammoQuirkShortIdNoUnderscore"] = w["WeaponStats"]["ammoType"].lower().replace("acammo", "").replace("ammo", "").replace("clan", "c").replace("-","").replace("silverbulletgauss", "silverbullet")
			if "hyperassaultgauss" in w["WeaponStats"]["ammoQuirkShortIdNoUnderscore"]:
				w["WeaponStats"]["ammoQuirkShortIdNoUnderscore"] = "chag40"
		else:
			w["WeaponStats"]["ammoQuirkShortIdNoUnderscore"] = ""

	
	global Weapons
	Weapons = weapons
	load_ammo_data_to_weapons(os.path.join(gamePath, r"Game\GameData\Libs\Items\Modules\Ammo.xml"))

	print("writing json:\n")
	with open('Weapons.json', 'w') as f:
		json.dump(weapons, f, indent=4, separators=(",", ": "), sort_keys=True)	

	write_modded_json_csv(weapons, "weapons.moddedjson.txt")
	
		#destination_dir = os.path.join(source_dir, mech_name)
	
def write_modded_json_csv(js, filename):
	output = convert_json_to_csv(json.dumps(js, indent=4, separators=(",", ": "), sort_keys=True))
	text_file = open(filename, "w")
	text_file.write(output)
	text_file.close()
	
def convert_json_to_csv(js):
	output = ""
	for line in js.splitlines():
		output += "\""+line.replace("\"", "`")+"\"\n"
	return output

def load_ammo_data_to_weapons(ammo_path):
	print("reading ammo: ", ammo_path)
	file = open(ammo_path, "r")
	tree = ET.parse(file)
	root = tree.getroot()

	data = defaultdict(dict)

	for aElement in root.iter("Module"):
		if("Half" not in aElement.get("name")):
			stats = aElement.find("AmmoTypeStats")
			data[stats.get("type")] = int(stats.get("numShots"))

	global Weapons
	for w in Weapons["weapons"]:
		if "ammoType" in Weapons["weapons"][w]["WeaponStats"]:
			Weapons["weapons"][w]["WeaponStats"]["ammoPerTon"] =  data[ Weapons["weapons"][w]["WeaponStats"]["ammoType"] ]
		else:
			Weapons["weapons"][w]["WeaponStats"]["ammoPerTon"] = ""


def read_mech_ids(mech_item_path):
	print("reading mech ids...")
	print("The source directory is:", mech_item_path)

	data = {
		"_GameVersion": GameVersion,
		"variants": defaultdict(dict),
		"chassis": defaultdict(dict)
	}
	
	file = open(mech_item_path, "r")
	tree = ET.parse(file)
	root = tree.getroot()

	# iterate through variants
	for v in root.iter("Mech"):
		data["variants"][v.get("name").upper()] = {
			"id": v.get("id"),
			"faction": v.get("faction"),
			"chassis": v.get("chassis"),
		}
		data["chassis"][v.get("chassis")]["faction"] = v.get("faction")

	global MechIDs
	MechIDs = data

def read_omnipod_ids(omnipod_item_path):
	print("reading mech ids...")
	print("The source directory is:", omnipod_item_path)

	data = {
		"_GameVersion": GameVersion,
		"Variants": defaultdict(dict)
	}
	
	file = open(omnipod_item_path, "r")
	tree = ET.parse(file)
	root = tree.getroot()

	# iterate through variants
	for v in root.iter("OmniPod"):
		if v.get("set").upper() not in data["Variants"]:
			data["Variants"][v.get("set").upper()] = defaultdict(dict)
		data["Variants"][v.get("set").upper()][v.get("component")] = v.get("id")

	global OmnipodIDs
	OmnipodIDs = data


def read_and_convert_mech_and_quirks(mech_dir):
	print("reading...")
	print("The source directory is:", mech_dir)

	data = {
		"_GameVersion": GameVersion,
		"mechs": defaultdict(dict)
	}

	quirkData = {
		"_GameVersion": GameVersion,
		"quirks": defaultdict(dict),
			# name 
			#	- aliases (flat list)
			#	- min, max, median, average (per IS/clan?)
		"quirkAliases": defaultdict(dict)
			# name
			# 	- hierarchy?
			# 	- aliases
			#
	}
	quirkSet = set()

	mechs = defaultdict(dict)
	
	# Create list of hardpoint aliases to determine component hardpoint list
	HardpointTypeAliases = defaultdict(dict)
	for w in Weapons["weapons"].values():
		weaponType = w["WeaponStats"]["type"]
		if weaponType in HardpointTypeAliases:
			HardpointTypeAliases[weaponType].update(w["HardpointAliases"]) 
		else:
			HardpointTypeAliases[weaponType] = set(w["HardpointAliases"])
	for ht in HardpointTypeAliases:
		HardpointTypeAliases[ht].update([ht])

	for file in os.listdir(mech_dir):
		if file.endswith(".pak"):
			mech_name = os.path.basename(file[:-4]).lower()
			
			fullrun = True or mech_name[0] == 'a'
			if fullrun:
				print("Found a zipped file:", mech_name)
				
				if(mech_name in MechIDs["chassis"]):
					data["mechs"][mech_name] = { "Variants": {}}
					data["mechs"][mech_name]["faction"] = MechIDs["chassis"][mech_name]["faction"]
				else:
					print("warning, mech not found in id list: "+ mech_name)
					continue	
				with zipfile.ZipFile(os.path.join(mech_dir, file), "r") as zip_ref:
					for member in zip_ref.namelist():
						if member.endswith(".mdf"):
							mechvariant = os.path.basename(member).split(".")[0].upper()
							openedFile = zip_ref.open(member)


							variant = {	}
							tree = ET.parse(openedFile)
							#print(tree)
							root = tree.getroot()
							baseStats = root.find("Mech").attrib
							if mechvariant in MechIDs["variants"]:
								baseStats["faction"] = MechIDs["variants"][mechvariant]["faction"]
								baseStats["id"] = MechIDs["variants"][mechvariant]["id"]
							else:
								baseStats["faction"] = "unknown"
								baseStats["id"] = ""
							baseStats["BaseTons"] = float(baseStats["BaseTons"])
							baseStats["MaxEngineRating"] = int(baseStats["MaxEngineRating"])
							baseStats["MaxJumpJets"] = int(baseStats["MaxJumpJets"]) if "MaxJumpJets" in baseStats else 0
							baseStats["MaxTons"] = float(baseStats["MaxTons"])
							baseStats["MinEngineRating"] = int(baseStats["MinEngineRating"])
							

							weightLimits = {"Light":[0,35], "Medium": [36,55], "Heavy": [56,75], "Assault": [76,100]}
							for className in weightLimits:
								if baseStats["MaxTons"] >= weightLimits[className][0] and baseStats["MaxTons"] <= weightLimits[className][1]:
									baseStats["class"] = className
							
							#print(baseStats)
							mechCanEquipECM = False
							components = {}
							for c in root.iter("Component"):
								cname = c.get("Name")
								components[cname] = {}
								components[cname]["HardpointIds"] = []
								for h in c.iter("Hardpoint"):
									components[cname]["HardpointIds"].append(int(h.get("ID")))

								if mechvariant in OmnipodIDs["Variants"] and cname in OmnipodIDs["Variants"][mechvariant]:
									components[cname]["OmnipodID"] = OmnipodIDs["Variants"][mechvariant][cname]
								#else:
								#	components[cname]["OmnipodID"] = ""

								canECM = c.get("CanEquipECM")
								if (canECM != None):
									components[cname]["CanEquipECM"] = canECM
									if(canECM == "1"):
										mechCanEquipECM = True
								#also get internal and fixed items (and slots?)
							quirks = {}
							for q in root.iter('Quirk'):
								if q.get("name").find("rear") == -1:
									quirks[q.get("name")] = float(q.get("value"))
									quirkSet.add(q.get("name"))

							variant["Stats"] = baseStats
							variant["Stats"]["ECMPartFound"] = mechCanEquipECM
							variant["ComponentList"] = components
							variant["QuirkList"] = quirks
							if baseStats["Variant"] == "ADR-A":
								print(variant)
							data["mechs"][mech_name]["Variants"][mechvariant] = variant #<- have to use file name cause pgi made spelling errors in xml
		
					for member in zip_ref.namelist():
						if os.path.basename(member).find("omnipods") >= 0:
							openedFile = zip_ref.open(member)
							tree = ET.parse(openedFile)
							root = tree.getroot()

							omniComponents = defaultdict(dict)							
							for s in root.iter("Set"):
								setName = s.get("name")
								if setName.upper() not in data["mechs"][mech_name]["Variants"]:
									print("error: mech found in omnipods but not mdf files - " + setName)
								else:
									data["mechs"][mech_name]["Variants"][setName.upper()]["isOmniMech"] = True
									omniComponents[setName]["SetBonuses"] = defaultdict(dict)

									# *** Set Bonuses ***
									data["mechs"][mech_name]["Variants"][setName.upper()]["SetBonuses"] = defaultdict(dict)
									for setBonus in s.iter("Bonus"):
										count = setBonus.get("PieceCount")
										quirks = {}
										for q in setBonus.iter('Quirk'):
											if q.get("name").find("rear") == -1:
												quirks[q.get("name")] = float(q.get("value"))
												quirkSet.add(q.get("name"))
										data["mechs"][mech_name]["Variants"][setName.upper()]["SetBonuses"][count] = quirks

									# *** Omnipod Component Bonuses ***
									mechCanEquipECM = False
									for component in s.iter("component"):
										quirks = {}
										hardpointIds = []
										for q in component.iter('Quirk'):
											quirks[q.get("name")] = float(q.get("value"))
											quirkSet.add(q.get("name"))
										for h in component.iter("Hardpoint"):
											hardpointIds.append(int(h.get("ID")))

										canECM = component.get("CanEquipECM")
										if (canECM != None):
											data["mechs"][mech_name]["Variants"][setName.upper()]["ComponentList"][component.get("name")]["CanEquipECM"] = canECM
											if(canECM == "1"):
												mechCanEquipECM = True

										data["mechs"][mech_name]["Variants"][setName.upper()]["ComponentList"][component.get("name")]["QuirkList"] = quirks
										data["mechs"][mech_name]["Variants"][setName.upper()]["ComponentList"][component.get("name")]["HardpointIds"] = hardpointIds
									data["mechs"][mech_name]["Variants"][setName.upper()]["Stats"]["ECMPartFound"] = mechCanEquipECM
																	
					for member in zip_ref.namelist():
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

							# Generate hardpoint index (id's to number of each hardpoint type)
							hardpointIndex = defaultdict(dict)
							for hardpoint in root.iter("Hardpoint"):
								id = int(hardpoint.get("id"))
								for w in hardpoint.iter("WeaponSlot"):
									names = []
									for a in w.iter("Attachment"):
										names.append(a.get("search"))
									attachmentType = get_weapon_type(names)
									if attachmentType in hardpointIndex[id]:
										hardpointIndex[id][attachmentType] += 1
									else:
										hardpointIndex[id][attachmentType] = 1

							# Assign hardpoint info to each mech component by matching with hardpoint id in index
							for vname,variant in data["mechs"][mech_name]["Variants"].items():
								for cname, component in variant["ComponentList"].items():
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
	
	#print(data)				
	print("writing json:\n")
	with open('Mechs.json', 'w') as f:
		json.dump(data, f, indent=4, separators=(",", ": "), sort_keys=True)					
		#destination_dir = os.path.join(source_dir, mech_name)

	write_modded_json_csv(data, "mechs.moddedjson.txt")
	
	quirklist = list(quirkSet)
	quirklist.sort()
	weaponquirkset = set()
	weaponAliases = set()
	qEffects = set()
	quirks =  defaultdict(dict)

	for w in Weapons["weapons"]:
		for a in Weapons["weapons"][w]["HardpointAliases"]:
			weaponAliases.add(a)

	
	for q in quirkSet:
		
		quirks[q] = { "MatchesWeapons": list() }
		matched = False
		words = q.split("_")
		if words[0] is not None:
			if matched is False and words[0] == "ammocapacity":
				matched == True
				qEffects.add("ammocapacity")
				weaponquirkset.add(q)
				quirklist.remove(q)
			else:
				if matched is False:
					if words[0] == "all":
						quirks[q]["MatchesWeapons"].append("all")
					else:
						for w in Weapons["weapons"]:
							for a in Weapons["weapons"][w]["HardpointAliases"]:
								if words[0].lower() == a.lower():
									quirks[q]["MatchesWeapons"].append(w)

					for a in weaponAliases:
						if words[0].lower() == a.lower() or words[0] == "all":
							matched = True
							qEffects.add(words[1])
							weaponquirkset.add(q)
							quirklist.remove(q)
							break
			if matched is False:
				qEffects.add("_".join( words[0:(len(words)-1)] ))
				matched = True
				#quirks[q]["MatchesWeapons"].append("none")

	for w in Weapons["weapons"]:
		shortId = Weapons["weapons"][w]["WeaponStats"]["ammoQuirkShortIdNoUnderscore"]
		if shortId != "":
			matchFound = False
			for q in quirks:
				if q.replace("ammocapacity", "").replace("additive", "").replace("_", "") == shortId:
					quirks[q]["MatchesWeapons"].append(w)
					quirks[q]["ammoPerTon"] = Weapons["weapons"][w]["WeaponStats"]["ammoPerTon"]
					matchFound = True
					break
					#ammoQuirkName = "ammocapacity_" + shortId + "_additive"
				#if (ammoQuirkName in quirks):
					#quirks[ammoQuirkName]["MatchesWeapons"].append(w)
					#quirks[ammoQuirkName]["ammoPerTon"] = Weapons["weapons"][w]["WeaponStats"]["ammoPerTon"]
					
			if(not matchFound):
				print("no ammo quirk found for " + w + "("+shortId+"). Maybe someday?")


	weaponquirklist = list(weaponquirkset)
	weaponquirklist.sort()
	qe = list(qEffects)
	qe.sort()
	quirkData["nonweaponquirkList"] = quirklist
	quirkData["weaponQuirkList"] = weaponquirklist
	quirkData["effects"] = qe
	quirkData["quirks"] = quirks
	with open('Quirks.json', 'w') as f:
		json.dump(quirkData, f, indent=4, separators=(",", ": "), sort_keys=True)
	
	write_modded_json_csv(quirkData, "quirks.moddedjson.txt")


def readVersion(source_file):
	print("reading version...", source_file)
	file = open(source_file, "r")
	data = file.read()
	tree = ET.XML(data.replace('ï»¿', ''))
	#root = tree.getroot()
	
	global GameVersion
	GameVersion = tree.find("BuildVersion").text


if __name__ == "__main__":
	#source_dir = os.getcwd()
	#copy_mdf_and_xml_files(source_dir)
	readVersion(os.path.join(gamePath, "build_info.xml"))
	read_and_convert_weapons(os.path.join(gamePath, r"Game\GameData\Libs\Items\Weapons\Weapons.xml"))
	read_mech_ids(os.path.join(gamePath, r"Game\GameData\Libs\Items\Mechs\Mechs.xml"))
	read_omnipod_ids(os.path.join(gamePath, r"Game\GameData\Libs\Items\OmniPods.xml"))
	read_and_convert_mech_and_quirks(os.path.join(gamePath, r"Game\mechs")) #reads possible quirks from mech data