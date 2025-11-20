import maya.cmds as cmds
import maya.api.OpenMaya as om2
import maya.api.OpenMayaAnim as om2Anim

# selection = cmds.ls(sl=True)

# if len(selection) < 2:
#     cmds.warning("Please select at least two objects to run the dummy script.")

# else:
#     orginal = selection[0]
#     replaced = selection[1]

#     replaced_children = cmds.listRelatives(replaced, shapes=True, fullPath=True) or []

#     original_dupe = cmds.duplicate(orginal, name=orginal + "_TEMP_DUPLICATE", renameChildren=True)[0]

#     dupe_children = cmds.listRelatives(original_dupe, shapes=True, fullPath=True) or []

#     cmds.delete(replaced_children)

#     for i, item in enumerate(dupe_children):
#         name = f"{replaced}Shape0{i}"
#         renamed = cmds.rename(item, name)
#         cmds.parent(renamed, replaced, shape=True, relative=True)

#     cmds.delete(original_dupe)


# for item in cmds.ls(sl=True):
#     cmds.setAttr(f"{item}.overrideEnabled", 1)
#     cmds.setAttr(f"{item}.overrideColor", 18)

sel = om2.MSelectionList()
sel.add("pSphere1")
shape_obj = sel.getDagPath(0)
print(shape_obj)

it = om2.MItDependencyGraph(
    shape_obj.node(),
    om2.MFn.kSkinClusterFilter,
    om2.MItDependencyGraph.kUpstream
)

skin_mobj = it.currentNode()
print(om2Anim.MFnSkinCluster(skin_mobj))