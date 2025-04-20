import maya.cmds as cmds
import maya.OpenMaya as om
import os
import json

class GuidesExport():

        def guides_export(self):
                self.guides_folder = cmds.ls(sl=True)
                answer = cmds.promptDialog(
                        title="INPUT DIALOG",
                        message="INSERT FILE NAME",
                        button=["OK", "Cancel"],
                        defaultButton="OK",
                        cancelButton="Cancel",
                        dismissString="Cancel")
                if answer == "Cancel":
                        return
                self.guides_name = cmds.promptDialog(query=True, text=True)

                if self.guides_folder:
                        self.guides_descendents = cmds.listRelatives(self.guides_folder[0], allDescendents=True, type="joint")
                        if not self.guides_descendents:
                                om.MGlobal.displayError("No guides found in the scene.")
                                return

                        left_guides = []
                        right_guides = []
                        for guide in self.guides_descendents:
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


                                                if left_world_position != right_world_position:
                                                        om.MGlobal.displayWarning(f"Guides are not symmetrical. {right_guide} is not in the same position as {left_guide}.")
                                                        return
                                                      

                        
                        if len(left_guides) != len(right_guides):
                                om.MGlobal.displayWarning("Guides are not symmetrical.")
                                return
                        
                        self.guides_world_matrix = [cmds.getAttr(f"{guide}.worldMatrix[0]") for guide in self.guides_descendents]
                        self.guides_parents = [cmds.listRelatives(guide, parent=True)[0] for guide in self.guides_descendents]



                else:
                        om.MGlobal.displayError("No guides found in the scene.")
                        return

                self.export_json()

        def export_json(self):

                complete_path = os.path.realpath(__file__)
                relative_path = complete_path.split("\scripts")[0]
                final_path = os.path.join(relative_path, "guides")
                self.guides_data = {self.guides_name: {}}

                for i, guide in enumerate(self.guides_descendents):
                        self.guides_data[self.guides_name][guide] = {
                                "worldPosition": self.guides_world_matrix[i],
                                "parent": self.guides_parents[i],
                        }

                if not os.path.exists(final_path):
                        os.makedirs(final_path)

                with open(os.path.join(final_path, f'{self.guides_name}.guides'), "w") as outfile:
                        json.dump(self.guides_data, outfile, indent=4)

                om.MGlobal.displayInfo(f"Guides data exported to {os.path.join(final_path, f'{self.guides_name}.json')}")


        def guide_import(self, joint_name, all_descendents=True):

                complete_path = os.path.realpath(__file__)
                relative_path = complete_path.split("\scripts")[0]
                guides_path = os.path.join(relative_path, "guides")

                final_path = cmds.fileDialog2(fileMode=1, caption="Select JSON file", dir=guides_path, okCaption="Select")

                if not final_path:
                        om.MGlobal.displayError("No file selected.")
                        return
                
                name = final_path[0].split("/")[-1].split(".")[0]

                with open(final_path[0], "r") as infile:
                        self.guides_data = json.load(infile)


                if not cmds.ls("C_guides_GRP"):
                        guides_node = cmds.createNode("transform", name="C_guides_GRP")
                else:
                        guides_node = "C_guides_GRP"
                
                if joint_name == "all":
                        for joint, data in reversed(list(self.guides_data[name].items())):
                                cmds.select(clear=True)
                                imported_joint = cmds.joint(name=joint, rad = 1 )
                                cmds.setAttr(f"{imported_joint}.offsetParentMatrix", data["worldPosition"], type="matrix")
                                if data["parent"]:
                                        if data["parent"] == "C_root_JNT":
                                                cmds.parent(imported_joint, guides_node)   
                                        else:
                                                cmds.parent(joint, data["parent"])                        


                else:
                        for main_joint_name, data in self.guides_data[name].items():
                                        if main_joint_name == joint_name:
                                                        cmds.select(clear=True) 
                                                        main_joint = cmds.joint(name=main_joint_name, rad=1)
                                                        cmds.setAttr(f"{main_joint}.offsetParentMatrix", data["worldPosition"], type="matrix")
                                                        cmds.parent(main_joint, guides_node)
                                                        break

                        if all_descendents:
                                parent_map = {joint: data["parent"] for joint, data in self.guides_data[name].items()}                                
                                processing_queue = [joint for joint, parent in parent_map.items() if parent == joint_name]
                                
                                while processing_queue:
                                                joint = processing_queue.pop(0)
                                                cmds.select(clear=True)
                                                imported_joint = cmds.joint(name=joint, rad=1)
                                                cmds.setAttr(f"{imported_joint}.offsetParentMatrix", self.guides_data[name][joint]["worldPosition"], type="matrix")
                                                parent = parent_map[joint]
                                                cmds.parent(imported_joint, guides_node if parent == "C_root_JNT" else parent)
                                                processing_queue.extend([child for child, parent in parent_map.items() if parent == joint])
                        
                cmds.select(clear=True)
                


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
