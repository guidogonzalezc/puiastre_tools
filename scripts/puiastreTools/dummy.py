import maya.cmds as cmds

for item in cmds.ls():
    if cmds.nodeType(item) == "transform":
        if "L_" in item and "_CTL" in item:
            if "Bendy" in item:
                cmds.setAttr(item + ".overrideEnabled", 1)
                cmds.setAttr(item + ".overrideColor", 18)  # Pink for Left Bendy
            else:
                cmds.setAttr(item + ".overrideEnabled", 1)
                cmds.setAttr(item + ".overrideColor", 6)  # Blue for Left side
        elif "R_" in item and "_CTL" in item:
            if "Bendy" in item:
                cmds.setAttr(item + ".overrideEnabled", 1)
                cmds.setAttr(item + ".overrideColor", 4)  # Light Blue for Right Bendy
            else:
                cmds.setAttr(item + ".overrideEnabled", 1)
                cmds.setAttr(item + ".overrideColor", 13)  # Red for Right side