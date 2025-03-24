import maya.cmds as cmds
import puiastreTools.tools.curve_tool as ctls_cre

class FingerModule(object):

    def __init__(self):
        self.main_finger = cmds.ls(sl=True)[0]
        self.finger_chain = cmds.listRelatives(self.main_finger, ad=True)
        self.finger_chain.append(self.main_finger)
        self.finger_chain.reverse()
        self.side = self.finger_chain[0].split("_")[0]

        self.original_controllers()
        self.fk_controllers()
        self.controllers_move()

    def original_controllers(self):

        self.ctls_originals = []
        self.end = []
        for i, jnt in enumerate(self.finger_chain):
            name = jnt.split("_")[1]
            ctl = ctls_cre.controller_creator(name=f"{self.side}_{name}Main")
            cmds.matchTransform(ctl[1][0], jnt)

            
            cmds.select(clear=True)
            joint = cmds.joint(name = f"{self.side}_{name}BlendMain_JNT")

            cmds.connectAttr(ctl[0] + ".worldMatrix[0]", joint + ".offsetParentMatrix")

            if self.ctls_originals:
                cmds.parent(ctl[1][0], self.ctls_originals[-1][0])

            self.ctls_originals.append(ctl)
            self.end.append(joint)


    def fk_controllers(self):

        self.ctls = []
        self.blend_joints = []
        for i, jnt in enumerate(self.finger_chain):
            name = jnt.split("_")[1]
            ctl = ctls_cre.controller_creator(name=f"{self.side}_{name}")
            cmds.matchTransform(ctl[1][0], jnt)

            
            cmds.select(clear=True)
            joint = cmds.joint(name = f"{self.side}_{name}Blend_JNT")

            cmds.connectAttr(ctl[0] + ".worldMatrix[0]", joint + ".offsetParentMatrix")

            self.ctls.append(ctl)
            self.blend_joints.append(joint)
        
    
    def controllers_move(self):
        points = [cmds.xform(jnt, q=True, ws=True, t=True) for jnt in self.finger_chain]
        curve = cmds.curve(d=1, p=points, name=f"{self.side}_fingerMain_CRV")
        cmds.rebuildCurve(curve, ch=True, rpo=True, rt=0, end=True, kr=False, kcp=False, kep=True, kt=False, s=11, d=3, tol=0.01)
        offset_crv = cmds.offsetCurve(curve, d=100, nr=[1, 0, 0], useGivenNormal=True , n="C_tongueOffset_CRV")[0]

        aim_trn_main = cmds.createNode("transform", n="C_tongueAim_GRP")


        mpas = []
        for i, ctl in enumerate(self.ctls):
            name = ctl[1][0].split("_")[1]
            decompose = cmds.createNode("decomposeMatrix", name=f"{self.side}_{name}_DCM")
            cmds.connectAttr(f"{ctl[1][0]}.worldMatrix[0]", f"{decompose}.inputMatrix")
            nearest_point = cmds.createNode("nearestPointOnCurve", name=f"{self.side}_{name}_NPC")
            cmds.connectAttr(f"{curve}.worldSpace[0]", f"{nearest_point}.inputCurve")
            cmds.connectAttr(f"{decompose}.outputTranslate", f"{nearest_point}.inPosition")
            parameter = cmds.getAttr(f"{nearest_point}.parameter")

            cmds.delete(nearest_point, decompose)

            mpas.append(cmds.createNode("motionPath", name=f"{self.side}_{name}_MPA"))
            cmds.setAttr(f"{mpas[i]}.uValue", parameter)
            cmds.connectAttr(f"{curve}.worldSpace[0]", f"{mpas[i]}.geometryPath")
            cmds.connectAttr(f"{mpas[i]}.allCoordinates", f"{ctl[1][0]}.translate")


        parameters = [cmds.getAttr(f"{mpa}.uValue") for mpa in mpas]

        bendy_joints = []
        for i in range(0, len(parameters)-1):
            distance_value = parameters[i+1] - parameters[i]
            distance_value = distance_value / 4

            for j in range(1, 4):
                mpa = cmds.createNode("motionPath", name=f"{self.side}_{name}_MPA")
                cmds.setAttr(f"{mpa}.uValue", parameters[i] + (distance_value * j))
                cmds.connectAttr(f"{curve}.worldSpace[0]", f"{mpa}.geometryPath")
                
                name = self.blend_joints[i].split("_")[1]
                ctl, ctl_grp = ctls_cre.controller_creator(name=f"{self.side}_{name}Bendy0{j}")
                print(ctl_grp)
                print(ctl)

                cmds.connectAttr(f"{mpa}.allCoordinates", f"{ctl_grp[0]}.translate")

                cmds.select(clear=True)
                joint = cmds.joint(name = f"{self.side}_{name}Bendy0{j}_JNT")
                cmds.connectAttr(ctl + ".worldMatrix[0]", joint + ".offsetParentMatrix")

                aim_trn = cmds.createNode("transform", n=f"C_tongue0{i}Aim_TRN", parent=aim_trn_main)

                mpa_offset = cmds.createNode("motionPath", n=f"C_tongue0{i}Offset_MPA")
                cmds.setAttr(mpa_offset + ".uValue", parameter)
                cmds.connectAttr(offset_crv + ".worldSpace", mpa_offset + ".geometryPath")
                cmds.connectAttr(mpa_offset + ".allCoordinates", aim_trn + ".translate")        


                if i == len(parameters)-2:
                    aim_helper = cmds.createNode("transform", n="C_tongueAimHelper_TRN", p=aim_trn_main)
                    cmds.connectAttr(mpa + ".allCoordinates", aim_helper + ".translate") 

                bendy_joints.append(joint)

        cmds.skinCluster(self.end, curve, tsb=True)


FingerModule()