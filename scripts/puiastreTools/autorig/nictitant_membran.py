import maya.cmds as cmds

class NictitantMembran:
    def __init__(self):
        self.project_joints()

    def project_joints(self):
        self.set_range = "setRange1"
        self.surface = "nurbsPlane1"

        for i in range(10):
            v_val = 0.1 * i
            joint = cmds.joint(n="nictitantMembran_0" + str(i) + "_jnt")
            pointOnSurface = cmds.createNode("pointOnSurfaceInfo", n="nictitantMembran_0" + str(i) + "_posi")
            cmds.connectAttr(self.set_range + ".outValueX", pointOnSurface + ".parameterU")
            cmds.setAttr(pointOnSurface + ".parameterV", v_val)
            cmds.connectAttr(self.surface + ".worldSpace", pointOnSurface + ".inputSurface")
            cmds.connectAttr(pointOnSurface + ".position", joint + ".translate")


nictitantMembran = NictitantMembran()
nictitantMembran.project_joints()
