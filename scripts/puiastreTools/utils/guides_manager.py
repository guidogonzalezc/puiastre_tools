import maya.cmds as cmds
import maya.OpenMaya as om
import os
import json


def guides_export():
        guides_folder = cmds.ls(sl=True)
        answer = cmds.promptDialog(
                title="INPUT DIALOG",
                message="INSERT FILE NAME",
                button=["OK", "Cancel"],
                defaultButton="OK",
                cancelButton="Cancel",
                dismissString="Cancel")
        if answer == "Cancel":
                return
        guides_name = cmds.promptDialog(query=True, text=True)

        if guides_folder:
                guides_descendents = cmds.listRelatives(guides_folder[0], allDescendents=True, type="joint")
                if not guides_descendents:
                        om.MGlobal.displayError("No guides found in the scene.")
                        return

                left_guides = []
                right_guides = []
                for guide in guides_descendents:
                        if guide.split("_")[0] == "L":
                                left_guides.append(guide)
                        if guide.split("_")[0] == "R":
                                right_guides.append(guide)
                for left_guide in left_guides:
                        splited_guide = left_guide.split("_")[1]
                        for right_guide in right_guides:
                                if splited_guide in right_guide:
                                        left_world_position = [round(coord, 3) for coord in cmds.xform(left_guide, q=True, ws=True, t=True)]
                                        right_world_position = [round(coord, 3) for coord in cmds.xform(right_guide, q=True, ws=True, t=True)]

                                        right_world_position[0] = right_world_position[0] * -1


                                        # if left_world_position != right_world_position:
                                        #         om.MGlobal.displayWarning(f"Guides are not symmetrical. {right_guide} is not in the same position as {left_guide}.")
                                        #         return
                                                

                
                if len(left_guides) != len(right_guides):
                        om.MGlobal.displayWarning("Guides are not symmetrical.")
                        return
                
                guides_get_rotation = [cmds.xform(guide, q=True, ws=True, rotation=True) for guide in guides_descendents]
                guides_get_translation = [cmds.xform(guide, q=True, ws=True, translation=True) for guide in guides_descendents]
                guides_parents = [cmds.listRelatives(guide, parent=True)[0] for guide in guides_descendents]
                guides_prefered_angle = [cmds.getAttr(f"{guide}.preferredAngle")[0] for guide in guides_descendents]



        else:
                om.MGlobal.displayError("No guides found in the scene.")
                return

        complete_path = os.path.realpath(__file__)
        relative_path = complete_path.split("\scripts")[0]
        final_path = os.path.join(relative_path, "guides")
        guides_data = {guides_name: {}}

        for i, guide in enumerate(guides_descendents):
                guides_data[guides_name][guide] = {
                        "worldPosition": guides_get_translation[i],
                        "worldRotation": guides_get_rotation[i],
                        "preferredAngle": guides_prefered_angle[i],     
                        "parent": guides_parents[i],
                }

        if not os.path.exists(final_path):
                os.makedirs(final_path)

        with open(os.path.join(final_path, f'{guides_name}.guides'), "w") as outfile:
                json.dump(guides_data, outfile, indent=4)

        om.MGlobal.displayInfo(f"Guides data exported to {os.path.join(final_path, f'{guides_name}.json')}")


def guide_import(joint_name, all_descendents=True, filePath=None):

        if not filePath:
                complete_path = os.path.realpath(__file__)
                relative_path = complete_path.split("\scripts")[0]
                guides_path = os.path.join(relative_path, "guides")

                final_path = cmds.fileDialog2(fileMode=1, caption="Select JSON file", dir=guides_path, okCaption="Select")[0]

                if not final_path:
                        om.MGlobal.displayError("No file selected.")
                        return
        else:
                final_path = os.path.normpath(filePath)

        name = os.path.basename(final_path).split(".")[0]

        with open(final_path, "r") as infile:
                guides_data = json.load(infile)



        
        joints_chain = []
        if joint_name == "all":
                if not cmds.ls("C_guides_GRP"):
                        guides_node = cmds.createNode("transform", name="C_guides_GRP")
                else:
                        guides_node = "C_guides_GRP"
                for joint, data in reversed(list(guides_data[name].items())):
                        cmds.select(clear=True)
                        imported_joint = cmds.joint(name=joint, rad = 50 )
                        cmds.setAttr(f"{imported_joint}.translate", data["worldPosition"][0], data["worldPosition"][1], data["worldPosition"][2])
                        cmds.setAttr(f"{imported_joint}.rotate", data["worldRotation"][0], data["worldRotation"][1], data["worldRotation"][2])
                        cmds.makeIdentity(imported_joint, apply=True, r=True)
                        cmds.setAttr(f"{imported_joint}.preferredAngle", data["preferredAngle"][0], data["preferredAngle"][1], data["preferredAngle"][2])
                        if data["parent"]:
                                if data["parent"] == "C_root_JNT":
                                        cmds.parent(imported_joint, guides_node)   
                                else:
                                        cmds.parent(joint, data["parent"])                        

        else:
                for main_joint_name, data in guides_data[name].items():
                                if main_joint_name == joint_name:
                                                cmds.select(clear=True) 
                                                main_joint = cmds.joint(name=main_joint_name, rad=50)
                                                cmds.setAttr(f"{main_joint}.translate", data["worldPosition"][0], data["worldPosition"][1], data["worldPosition"][2])
                                                cmds.setAttr(f"{main_joint}.rotate", data["worldRotation"][0], data["worldRotation"][1], data["worldRotation"][2])
                                                cmds.makeIdentity(main_joint, apply=True, r=True)
                                                cmds.setAttr(f"{main_joint}.preferredAngle", data["preferredAngle"][0], data["preferredAngle"][1], data["preferredAngle"][2])
                                                joints_chain.append(main_joint_name)
                                                break

                if all_descendents:
                        parent_map = {joint: data["parent"] for joint, data in guides_data[name].items()}                                
                        processing_queue = [joint for joint, parent in parent_map.items() if parent == joint_name]      
                        
                        while processing_queue:
                                        joint = processing_queue.pop(0)
                                        cmds.select(clear=True)
                                        imported_joint = cmds.joint(name=joint, rad=50)
                                        cmds.setAttr(f"{imported_joint}.translate", guides_data[name][joint]["worldPosition"][0], guides_data[name][joint]["worldPosition"][1], guides_data[name][joint]["worldPosition"][2])
                                        cmds.setAttr(f"{imported_joint}.rotate", guides_data[name][joint]["worldRotation"][0], guides_data[name][joint]["worldRotation"][1], guides_data[name][joint]["worldRotation"][2])
                                        cmds.makeIdentity(imported_joint, apply=True, r=True)
                                        cmds.setAttr(f"{imported_joint}.preferredAngle", data["preferredAngle"][0], data["preferredAngle"][1], data["preferredAngle"][2])  
                                        parent = parent_map[joint]
                                        if parent != "C_root_JNT":
                                                cmds.parent(imported_joint, parent)
                                        joints_chain.append(joint)
                                        processing_queue.extend([child for child, parent in parent_map.items() if parent == joint])
                
        cmds.select(clear=True)
        if joints_chain:
                return joints_chain
        
        # return guides_node


""" EXECUTE THE CODE IN MAYA SCRIPT EDITOR FOR EXPORTING

from puiastreTools.utils import guides_export
from importlib import reload
reload(guides_export)
guides_export.GuidesExport().guides_export()

"""

""" EXECUTE THE CODE IN MAYA SCRIPT EDITOR FOR IMPORTING

from puiastreTools.utils import guide_import
from importlib import reload
reload(guides_import)
guides_import.GuidesExport().guide_import("azhurean_guides")

"""
