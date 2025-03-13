import maya.cmds as cmds

class WingFinger():
    def __init__(self):
        self.wing_finger_guides = ["L_index01_JNT", "L_index02_JNT", "L_index03_JNT", "L_index04_JNT"]
        self.side = self.wing_finger_guides[0].split("_")[0]
        self.finger = ''.join(filter(str.isalpha, self.wing_finger_guides[0].split("_")[1]))

    def pairblends():
        pass
    
    def controllers():
        pass

    



    def curvature_setup(self):
        print(self.finger)
        linearArmCurve = "curve3"

        bezierArmCurve = cmds.duplicate(linearArmCurve, name=f"{self.side}_{self.finger}Bezier_CRV", renameChildren=True)[0]

        commands = [
            (bezierArmCurve, lambda: cmds.nurbsCurveToBezier()),
            # (f"{bezierArmCurve}.cv[*]", lambda: cmds.bezierAnchorPreset(preset=2)),
            ((f"{bezierArmCurve}.cv[0]", f"{bezierArmCurve}.cv[1]"), lambda: cmds.bezierAnchorPreset(preset=2)),
            ((f"{bezierArmCurve}.cv[8]", f"{bezierArmCurve}.cv[9]"), lambda: cmds.bezierAnchorPreset(preset=2)),
        ]

        for selection, action in commands:
            cmds.select(selection, r=True)
            action()

        cmds.bezierAnchorState(smooth=True, even=True)

        degree2 = cmds.duplicate(linearArmCurve, name=f"{self.side}_{self.finger}Degree2_CRV", renameChildren=True)[0]
        cmds.rebuildCurve(degree2, s=4, d=2)

        names = ["upperStart", "upperMid", "upperEnd", "lowerStart", "lowerMid", "lowerEnd"]

        locators = []
        for i in range(2,8):
            pos = cmds.pointPosition(f"{bezierArmCurve}.cv[{i}]")
            locators.append(cmds.spaceLocator(name=f"{self.side}_{self.finger}{names[i-2]}_LOC")[0])
            cmds.move(pos[0], pos[1], pos[2], locators[-1], a=True, ws=True)

        cmds.parent(locators[0], locators[2], locators[1])
        cmds.parent(locators[3], locators[5], locators[4])

        cmds.pointConstraint(self.wing_finger_guides[1], locators[1], mo=True)
        cmds.orientConstraint(self.wing_finger_guides[1], self.wing_finger_guides[0], locators[1], mo=True) 

        cmds.pointConstraint(self.wing_finger_guides[2], locators[4], mo=True)
        cmds.orientConstraint(self.wing_finger_guides[2], self.wing_finger_guides[1], locators[4], mo=True)


        cv_controls = [self.wing_finger_guides[0], locators[0], locators[2], locators[3], locators[5], self.wing_finger_guides[3]]
        for i, controls in enumerate(cv_controls):
            dcmp = cmds.createNode("decomposeMatrix", name=f"{self.side}_{self.finger}0{i+1}_DCM")
            cmds.connectAttr(f"{controls}.worldMatrix[0]", f"{dcmp}.inputMatrix")
            cmds.connectAttr(f"{dcmp}.outputTranslate", f"{degree2}.controlPoints[{i}]")

            


WingFinger().curvature_setup()
