# Python libraries import
import os
import json
from importlib import reload

# Maya commands import
from maya.api import OpenMaya as om
import maya.cmds as cmds

# PuiastreTools imports
from puiastreTools.utils import core
import re

reload(core)

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__)).split("\scripts")[0]

def asset_structure_creation(asset_name, model_path = False, guides_path = False, curves_path = False, skinning_path = False, asset_type = "CHAR"):
    """
    Function to create the basic asset folder structure.

    This function creates the necessary folder structure for a new asset
    """
    
    # Create main asset folder
    asset_path = os.path.join(SCRIPT_PATH, "assets", asset_name)
    if not os.path.exists(asset_path):
        os.makedirs(asset_path)
    else:
        # Asset folder already exists
        om.MGlobal.displayInfo(f"The asset folder already exists at: {asset_path}")
        return

    core.DataManager.clear_data()
    core.DataManager.set_project_path(asset_path)
    core.DataManager.set_asset_name(asset_name)
    
    configurations = {"asset_type": asset_type}
    # Create subfolders and handle custom paths
    extensions = [".guides", ".json", ".skn"]
    for i, (folder_names, path) in enumerate([("models", model_path), ("guides", guides_path), ("curves", curves_path), ("skinning", skinning_path)]):
        
        folder_path = os.path.join(asset_path, folder_names)
        
        if not os.path.exists(folder_path) and not path:
            os.makedirs(folder_path)
            configurations[folder_names] = "relative"

        elif path:
            if os.path.exists(path):
                folder_path = path
                configurations[folder_names] = folder_path
            else:
                om.MGlobal.displayError(f"The provided path for {folder_names} directory does not exist: {path}")
                return
        else:
            om.MGlobal.displayInfo(f"The {folder_names} directory already exists at: {folder_path}")
            configurations[folder_names] = "relative"
            return
        om.MGlobal.displayInfo(f"Asset folder structure created at: {asset_path}")

        # Create initial files in each subfolder
        if not folder_names == "models":
            initial_file = os.path.join(folder_path, f"{asset_type.upper()}_{asset_name}_001{extensions[i-1]}")
            if not os.path.exists(initial_file):
                with open(initial_file, 'w') as config_file:
                    json.dump(configurations, config_file, indent=4)
                om.MGlobal.displayInfo(f"Configuration file created at: {initial_file}")
            else:
                om.MGlobal.displayInfo(f"Configuration file already exists at: {initial_file}")
        else:
            cmds.file(new=True, force=True)
            cmds.file(rename=os.path.join(folder_path, f"{asset_type.upper()}_{asset_name}_0001.ma"))
            cmds.createNode("transform", name="skelMesh")
            cmds.createNode("transform", name="proxyMesh")
            cmds.createNode("transform", name="model")
            cmds.file(save=True, type="mayaAscii")



        # Store paths in DataManager
        if folder_names == "guides":
            core.DataManager.set_guide_data(folder_path)
        elif folder_names == "curves":
            core.DataManager.set_ctls_data(folder_path)
        elif folder_names == "skinning":
            core.DataManager.set_skinning_data(folder_path)

    # Create configuration file for setting relative or absolute paths
    config_file_path = os.path.join(asset_path, f"{asset_type.upper()}_{asset_name}_Paths.config")
    if not os.path.exists(config_file_path):
        with open(config_file_path, 'w') as config_file:
            json.dump(configurations, config_file, indent=4)
        om.MGlobal.displayInfo(f"Configuration file created at: {config_file_path}")
    else:
        om.MGlobal.displayInfo(f"Configuration file already exists at: {config_file_path}")

def _highest_version_file_in_directory(folder_path, extension):
    """
    Function to load the highest versioned model file from a directory.
    Args:
        folder_path (str): The directory path to search for model files.
        extension (str): The file extension to look for (e.g., ".ma").
    """
    file_path = None
    candidates = []
    for fname in os.listdir(folder_path):
        if not fname.lower().endswith(extension):
            continue
        candidates.append((os.path.join(folder_path, fname)))
    if candidates:
        candidates.sort()
        file_path = candidates[-1]
    return file_path

def load_asset_configuration(asset_name):
    """
    Function to load asset configuration from the configuration file.

    This function reads the configuration file for the specified asset
    and sets the paths in the DataManager accordingly.
    """
    asset_path = os.path.join(SCRIPT_PATH, "assets", asset_name)
    
    # List files ending with .config on asset_path
    config_files = []
    if os.path.exists(asset_path):
        for fname in os.listdir(asset_path):
            full_path = os.path.join(asset_path, fname)
            if os.path.isfile(full_path) and fname.lower().endswith('.config') and asset_name in fname:
                config_files.append(full_path)

    # If multiple .config files are found, use the first one
    if config_files:
        om.MGlobal.displayInfo("Configuration files found:\n" + "\n".join(config_files))
        config_file_path = config_files[0]  # use the first .config found
    else:
        om.MGlobal.displayInfo(f"No .config files found in: {asset_path}")
        return

    with open(config_file_path, 'r') as config_file:
        configurations = json.load(config_file)


    for folder_names, path in configurations.items():
        if path == "relative":
            folder_path = os.path.join(asset_path, folder_names)
        else:
            folder_path = path

        if folder_names == "guides":
            highest_version_file = _highest_version_file_in_directory(folder_path, ".guides")
            if highest_version_file:
                core.DataManager.set_guide_data(highest_version_file)
            else:
                om.MGlobal.displayInfo(f"No matching .guides files found in: {folder_path}")
                return

        elif folder_names == "curves":
            highest_version_file = _highest_version_file_in_directory(folder_path, ".json")
            if highest_version_file:
                core.DataManager.set_ctls_data(highest_version_file)
            else:
                om.MGlobal.displayInfo(f"No matching .curves files found in: {folder_path}")
                return

        elif folder_names == "skinning":
            highest_version_file = _highest_version_file_in_directory(folder_path, ".skn")
            if highest_version_file:
                core.DataManager.set_skinning_data(highest_version_file)
                om.MGlobal.displayInfo(f"Skinning file loaded from: {highest_version_file}")
            else:
                om.MGlobal.displayInfo(f"No matching .skn files found in: {folder_path}")
                return
            
        elif folder_names == "models":
            if os.path.exists(folder_path):
                highest_version_file = _highest_version_file_in_directory(folder_path, ".ma")

                if highest_version_file:
                    cmds.file(highest_version_file, o=True, f=True)
                    om.MGlobal.displayInfo(f"Model loaded from: {highest_version_file}")
                else:
                    om.MGlobal.displayInfo(f"No matching .ma files found in: {folder_path}")
            else:
                folder_path = os.path.join(asset_path, "models")
                highest_version_file = _highest_version_file_in_directory(folder_path, ".ma")

                if highest_version_file:
                    cmds.file(highest_version_file, o=True, f=True)
                    om.MGlobal.displayInfo(f"Model loaded from: {highest_version_file}")
                else:
                    om.MGlobal.displayInfo(f"No matching .ma files found in: {folder_path}")
                om.MGlobal.displayError(f"Models folder does not exist repathed to: {folder_path}")
                return


    core.DataManager.set_asset_name(asset_name)
    core.DataManager.set_project_path(asset_path)
    om.MGlobal.displayInfo(f"Asset configuration loaded for: {asset_name}")

# asset_structure_creation("rigoberta", asset_type="CHAR")
