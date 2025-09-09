import maya.cmds as cmds
import maya.OpenMaya as om
import os
import json
from puiastreTools.utils import core
from puiastreTools.utils import data_export
from importlib import reload
reload(core)

def guides_export(skelTree = None):
        """
        Exports the guides from the selected folder in the Maya scene to a JSON file.
        """

        # TEMPLATE_FILE = core.init_template_file(ext=".guides", file_name=f"{file_name}_")
        TEMPLATE_FILE = core.init_template_file(ext=".guides")
        print(f"Exporting guides to {TEMPLATE_FILE}")
        
        guides_folder = cmds.ls("guides_GRP", type="transform")

        if guides_folder:
                guides_descendents = [
                                node for node in cmds.listRelatives(guides_folder[0], allDescendents=True, type="transform")
                                if "buffer" not in node.lower() and "_guide_crv" not in node.lower()
                ]


                if not guides_descendents:
                        om.MGlobal.displayError("No guides found in the scene.")
                        return

                guides_get_translation = [cmds.xform(guide, q=True, ws=True, translation=True) for guide in guides_descendents]
                guides_parents = [cmds.listRelatives(guide, parent=True)[0] for guide in guides_descendents]
                guides_joint_twist = []
                guides_type = []
                guides_module_name = []
                guides_prefix_name = []

                for guide in guides_descendents:
                        # Try to get 'jointTwist' attribute, if not present, set value as 'Child'
                        if cmds.attributeQuery("jointTwist", node=guide, exists=True):
                                joint_twist = cmds.getAttr(f"{guide}.jointTwist")
                        else:
                                joint_twist = "Child"
                        guides_joint_twist.append(joint_twist)

                        # Try to get 'type' attribute, if not present, set value as 'Child'
                        if cmds.attributeQuery("type", node=guide, exists=True):
                                guide_type = cmds.getAttr(f"{guide}.type")
                        else:
                                guide_type = "Child"
                        guides_type.append(guide_type)

                        # Try to get 'moduleName' attribute, if not present, set value as 'Child'
                        if cmds.attributeQuery("moduleName", node=guide, exists=True):
                                index = cmds.getAttr(f"{guide}.moduleName")
                                enum_string = cmds.addAttr(f"{guide}.moduleName", q=True, en=True)
                                enum_list = enum_string.split(":")
                                module_name = enum_list[index]  
                        else:
                                module_name = "Child"
                        guides_module_name.append(module_name)
                        

                        if cmds.attributeQuery("prefix", node=guide, exists=True):
                                index = cmds.getAttr(f"{guide}.prefix")
                                enum_string = cmds.addAttr(f"{guide}.prefix", q=True, en=True)
                                enum_list = enum_string.split(":")
                                prefix_name = enum_list[index]  
                        else:
                                prefix_name = "Child"
                        guides_prefix_name.append(prefix_name)



        else:
                om.MGlobal.displayError("No guides found in the scene.")
                return
        
        guides_name = core.DataManager.get_asset_name() if core.DataManager.get_asset_name() else os.path.splitext(os.path.basename(TEMPLATE_FILE))[0]
        ctl_path = core.DataManager.get_ctls_data() if core.DataManager.get_ctls_data() else None
        mesh_path = core.DataManager.get_mesh_data() if core.DataManager.get_mesh_data() else None

        guides_data = {guides_name: {},
                       "controls": ctl_path,
                       "meshes": mesh_path,
                       "hierarchy": skelTree
                       }

        for i, guide in enumerate(guides_descendents):
                guides_data[guides_name][guide] = {
                        "worldPosition": guides_get_translation[i],
                        "parent": guides_parents[i],
                        "jointTwist": guides_joint_twist[i],
                        "type": guides_type[i],
                        "moduleName": guides_module_name[i],
                        "prefix": guides_prefix_name[i]
                }


        with open(os.path.join(TEMPLATE_FILE), "w") as outfile:
                json.dump(guides_data, outfile, indent=4)

        om.MGlobal.displayInfo(f"Guides data exported to {TEMPLATE_FILE}")

def get_data(name, module_name=False):

    final_path = core.init_template_file(ext=".guides", export=False)

    try:
        with open(final_path, "r") as infile:
            guides_data = json.load(infile)
    except Exception as e:
        if module_name:
            return None, None, None, None
        else:
            return None, None

    for template_name, guides in guides_data.items():
        if not isinstance(guides, dict):
            continue
        for guide_name, guide_info in guides.items():
            if name in guide_name:
                world_position = guide_info.get("worldPosition")
                parent = guide_info.get("parent")
                if module_name:
                        moduleName = guide_info.get("moduleName")
                        prefix = guide_info.get("prefix")
                        return world_position, parent, moduleName, prefix
                else:
                    return world_position, parent
    if module_name:
        return None, None, None, None
    else:
        return None, None


def guide_import(joint_name, all_descendents=True, path=None):
        """
        Imports guides from a JSON file into the Maya scene.
        
        Args:
                joint_name (str): The name of the joint to import. If "all", imports all guides.
                all_descendents (bool): If True, imports all descendents of the specified joint. Defaults to True.
        Returns:
                list: A list of imported joint names if joint_name is not "all", otherwise returns the world position and rotation of the specified joint.
        """
        
        data_exporter = data_export.DataExport()
        guides_grp = data_exporter.get_data("basic_structure", "guides_GRP")


        if cmds.objExists(guides_grp):
                guide_grp = guides_grp
        else:
                guide_grp = cmds.createNode("transform", name="guides_GRP")

        transforms_chain_export = []

        if all_descendents:
                
                if all_descendents is True:
                        world_position, parent, moduleName, prefix = get_data(joint_name, module_name=True)
                        guide_transform = cmds.createNode('transform', name=joint_name)
                        cmds.xform(guide_transform, ws=True, t=world_position)
                        cmds.parent(guide_transform, guide_grp)
                        transforms_chain_export.append(guide_transform)
                        if moduleName != "Child":
                               cmds.addAttr(guide_transform, longName="moduleName", attributeType="enum", enumName=moduleName, keyable=False)
                        if prefix != "Child":
                               cmds.addAttr(guide_transform, longName="prefix", attributeType="enum", enumName=prefix, keyable=False)


                        final_path = core.init_template_file(ext=".guides", export=False)
                        with open(final_path, "r") as infile:
                                        guides_data = json.load(infile)

                        guide_set_name = next(iter(guides_data))
                        parent_map = {joint: data.get("parent") for joint, data in guides_data[guide_set_name].items()}
                        transforms_chain = []
                        processing_queue = [joint for joint, parent in parent_map.items() if parent == joint_name]

                        while processing_queue:
                                joint = processing_queue.pop(0)
                                if "Settings" in joint:
                                        continue
                                cmds.select(clear=True)
                                imported_transform = cmds.createNode('transform', name=joint)
                                position = guides_data[guide_set_name][joint]["worldPosition"]
                                cmds.xform(imported_transform, ws=True, t=position)
                                parent = parent_map[joint]
                                if parent and parent != "C_root_JNT":
                                                cmds.parent(imported_transform, parent)
                                transforms_chain.append(joint)
                                children = [child for child, p in parent_map.items() if p == joint]
                                processing_queue.extend(children)
                                transforms_chain_export.append(imported_transform)
                                                         
        
        
        else:
                world_position, parent, moduleName, prefix = get_data(joint_name, module_name=True)
                guide_transform = cmds.createNode('transform', name=joint_name)
                cmds.xform(guide_transform, ws=True, t=world_position)
                cmds.parent(guide_transform, guide_grp)
                transforms_chain_export.append(guide_transform)
                if moduleName != "Child":
                        cmds.addAttr(guide_transform, longName="moduleName", attributeType="enum", enumName=moduleName, keyable=False)
                if prefix != "Child":
                        cmds.addAttr(guide_transform, longName="prefix", attributeType="enum", enumName=prefix, keyable=False)

        return transforms_chain_export
               
# guides_export()