import maya.cmds as cmds
from puiastreTools.tools.curve_tool import controller_creator



def lock_attr(ctl, attrs = ["scaleX", "scaleY", "scaleZ", "visibility"]):
    for attr in attrs:
        cmds.setAttr(f"{ctl}.{attr}", keyable=False, channelBox=False, lock=True)

def create_basic_structure(asset_name = "assetName"):

    folder_structure = {
        asset_name: {
            "controls_GRP": {
                "C_characterNode",
                "C_masterWalk",
                "C_preferences"

            },
            "rig_GRP": {
                "modules_GRP",
                "skel_GRP",
                "geoLayering_GRP",
                "skeletonHirearchy_GRP"
            },
            "model_GRP": {},
            "groom_GRP": {},
            "clothSim_GRP": {}
        }
    }

    main_transform = cmds.createNode("transform", name=asset_name)

    ctls = []
    secondary_transforms = []
    rig_transforms = []

    for folder, subfolders in folder_structure[asset_name].items():
        secondary_transform = cmds.createNode("transform", name=folder, parent=main_transform)
        secondary_transforms.append(secondary_transform)
        for subfolder in subfolders:
            if subfolder.startswith("C_"):
                ctl, grp = controller_creator(subfolder, ["GRP", "ANM"])
                cmds.setAttr(f"{ctl}.overrideEnabled", 1)
                if ctls:
                    cmds.parent(grp[0], ctls[-1])
                else:
                    cmds.parent(grp[0], secondary_transform)  
                ctls.append(ctl)
            else:
                trn = cmds.createNode("transform", name=subfolder, parent=secondary_transform)
                rig_transforms.append(trn)



            

            cmds.setAttr(f"{ctl[0]}.overrideColor", 14)
            cmds.addAttr(ctl[0], shortName="reference", niceName="Reference",attributeType="bool", keyable=False)
            cmds.setAttr(ctl[0]+".reference", channelBox=True)
            cmds.setAttr(rig_transforms[0]+".overrideDisplayType", 2)
            cmds.connectAttr(ctl[0]+".reference", rig_transforms[2]+".overrideEnabled")
            
            cmds.setAttr(f"{transform}.overrideColor", 17)
            cmds.addAttr(transform, shortName="extraAttributesSep", niceName="EXTRA ATTRIBUTES_____", enumName="_____",attributeType="enum", keyable=True)
            cmds.addAttr(transform, shortName="globalScale", niceName="Global Scale", minValue=0.001,defaultValue=1, keyable=True)
            cmds.setAttr(transform+".extraAttributesSep", channelBox=True, lock=True)
            cmds.connectAttr(transform+".globalScale", transform+".scaleX", force=True)
            cmds.connectAttr(transform+".globalScale", transform+".scaleY", force=True)
            cmds.connectAttr(transform+".globalScale", transform+".scaleZ", force=True)
            cmds.setAttr(f"{transform}.overrideColor", 6)
            cmds.setAttr(attribute, lock=True, keyable=False, channelBox=False)






""""

    SETS WIP


    sets = {         
        f"{asset_name}_RIG_SET": {
            "__EXPORT__SET": {
                "__EXPORT__GEO_SET": {
                    secondary_transforms[4],
                    secondary_transforms[3],
                    secondary_transforms[2],
                },
                "__EXPORT__LOCATORS_SET": {},
                "__EXPORT__SKELETON_HIERARCHY_SET": {
                    rig_transforms[3]
                }

            },
            "CONTROLS_SET": {
                ctls[0],
                ctls[1],
                ctls[2],
            }
        }
    }

    set_node = cmds.sets(name=f"{asset_name}_RIG_SET", empty=True)
    for set_name, contents in sets[f"{asset_name}_RIG_SET"].items():
        secondary_set = cmds.sets(name=set_name, empty=True)
        cmds.sets(secondary_set, add=set_node)
        for item, inside in contents.items():
            print(item)
            print(inside)
            if item == "__EXPORT__SET":
                export_set = cmds.sets(name=item, empty=True)
                cmds.sets(export_set, add=secondary_set)

            else:
                cmds.sets(item, add=secondary_set)

         
"""



create_basic_structure()