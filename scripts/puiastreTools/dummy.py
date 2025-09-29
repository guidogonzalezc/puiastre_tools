import maya.cmds as cmds

for item in cmds.ls(sl=True):
    if cmds.nodeType(item) == "transform":
        if "_CTL" in item:
            cmds.setAttr(item + ".overrideEnabled", 1)
            cmds.setAttr(item + ".overrideColor", 13)  # Pink for Left Bendy