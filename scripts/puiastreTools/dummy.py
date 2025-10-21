import maya.cmds as cmds

mirror_transform = cmds.createNode("transform", name="mirror_transform")

dupes = []

for item in cmds.listRelatives("guides_GRP", children=True) or []:
    if "L_" in item:
        dupe = cmds.duplicate(item, name=item + "_mirror")
        print(dupe)
        cmds.parent(dupe[0], mirror_transform)
        dupes.append(dupe[0])


# print(mirror_transform)
cmds.setAttr(f"{mirror_transform}.scaleX", -1)
# r_side = []
# for item in cmds.ls(sl=True) or []:
#     if "R_" in item:
#         r_side.append(item)

# for item in r_side:
#     for dupe_item in dupes:
#         if item.replace("R_", "L_").replace("_mirror", "") == dupe_item:
#             cmds.matchTransform(dupe_item, item, pos=True, rot=False)