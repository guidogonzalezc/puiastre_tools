import maya.cmds as cmds

def popUp():
    if cmds.window("popupWindow", exists=True):
        cmds.deleteUI("popupWindow")
    cmds.window("popupWindow", title="Warning Window", widthHeight=(200, 100), s=False)
    form = cmds.formLayout("formLayout")
    text = cmds.text(align="center", label="This is a warning message", height=35, parent=form)
    cmds.separator(height=5, style='none', parent=form)  # Add space between text and button
    button = cmds.button(label="Create Sphere", command="cmds.polySphere(n='True')", width=50, parent=form)
    cmds.showWindow("popupWindow")

popUp()