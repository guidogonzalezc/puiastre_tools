import maya.cmds as cmds
import puiastreTools.tools.curve_tool as ctls
from importlib import reload
reload(ctls)


class tailModule(object):
    def __init__(self):
        self.tail_crv = "C_tail_CRV"
        self.json = "S:/temp/.Easter/puiastre_tools/curves/foot_ctl.json"


    def create_nurbs(self):
        self.module_trn = cmds.createNode("transform", n="C_tailModule_GRP")
        self.out_skinJoints = cmds.createNode("transform", n="C_tailOutSkinJoints_GRP")
        self.driver_joints = cmds.createNode("transform", n="C_tailDriverJoints_GRP", p=self.module_trn) 

        cmds.parent(self.tail_crv, self.module_trn)

        dupe = cmds.duplicate(self.tail_crv, n="C_tailRebuild_CRV")[0]

        self.rebuild_curve = cmds.rebuildCurve(dupe, ch=0, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=4, d=3, tol=0.01)[0]

        num_cvs = cmds.ls(self.tail_crv + ".cv[*]", fl=True)
        print(num_cvs)

        controller_cvs = len(num_cvs) - 1


        tail_ctls = []
        tail_grps = []
        crv_skin_joints = []
        for i, cv in enumerate(num_cvs):
            tail_ctl, tail_grp = ctls.controller_creator(f"C_tail0{i+1}")
            cmds.xform(tail_grp, ws=True, t=cmds.pointPosition(cv))

            cmds.select(cl=True)
            joint = cmds.joint(n=f"C_tail0{i+1}Driver_JNT")
            cmds.parent(joint, self.driver_joints)
            
            cmds.connectAttr(tail_ctl + ".worldMatrix", joint + ".offsetParentMatrix")

            if tail_ctls:
                cmds.parent(tail_grp, tail_ctls[-1])

            tail_ctls.append(tail_ctl)  
            tail_grps.append(tail_grp)
            crv_skin_joints.append(joint)

        
        cmds.skinCluster(crv_skin_joints, self.rebuild_curve, tsb=True, n="C_tail_skinCluster")

        self.project_joints()

    def project_joints(self):
        
        num_cvs = cmds.ls(self.tail_crv + ".cv[*]", fl=True)

        offset_crv = cmds.offsetCurve(self.rebuild_curve, d=0.5, nr=[1, 0, 0], useGivenNormal=True , n="C_tailOffset_CRV")[0]
        cmds.parent(offset_crv, self.module_trn)

        aim_trn_main = cmds.createNode("transform", n="C_tailAim_GRP", p=self.module_trn)

        skinning_joints = []
        aimer_trn= []
        compose_matrix = []
        for i, cv in enumerate(num_cvs):
            cmds.select(cl=True)
            joint = cmds.joint(n=f"C_tail0{i}Skinned_JNT")
            aim_trn = cmds.createNode("transform", n=f"C_tail0{i}Aim_TRN", parent=aim_trn_main)
            cmds.parent(joint, self.out_skinJoints)
            

            nearest_point = cmds.createNode("nearestPointOnCurve", n=f"C_tail0{i}_NPOC")
            cmds.connectAttr(self.rebuild_curve + ".worldSpace", nearest_point + ".inputCurve")
            cv_pos = cmds.pointPosition(cv, world=True)
            cmds.setAttr(nearest_point + ".inPosition", cv_pos[0], cv_pos[1], cv_pos[2])

            parameter = cmds.getAttr(nearest_point + ".parameter")

            mpa = cmds.createNode("motionPath", n=f"C_tail0{i}_MPA")
            cmds.setAttr(mpa + ".uValue", parameter)
            cmds.connectAttr(self.rebuild_curve + ".worldSpace", mpa + ".geometryPath")
            cmds.connectAttr(mpa + ".allCoordinates", joint + ".translate") 

            compose_matrix.append(cmds.createNode("composeMatrix", n=f"C_tail0{i}_CMP"))
            cmds.connectAttr(mpa + ".allCoordinates", compose_matrix[i] + ".inputTranslate")

            mpa_offset = cmds.createNode("motionPath", n=f"C_tail0{i}Offset_MPA")
            cmds.setAttr(mpa_offset + ".uValue", parameter)
            cmds.connectAttr(offset_crv + ".worldSpace", mpa_offset + ".geometryPath")
            cmds.connectAttr(mpa_offset + ".allCoordinates", aim_trn + ".translate")        


            if i == len(num_cvs)-2:
                aim_helper = cmds.createNode("transform", n="C_tailAimHelper_TRN", p=aim_trn_main)
                cmds.connectAttr(mpa + ".allCoordinates", aim_helper + ".translate") 


            aimer_trn.append(aim_trn)
            skinning_joints.append(joint)
            cmds.delete(nearest_point)

        print(compose_matrix)
        print(aimer_trn)
        print(skinning_joints)  

        for j, aim in enumerate(aimer_trn):
            aim_matrix = cmds.createNode("aimMatrix", n=f"C_tail0{j}_AMX")
            cmds.connectAttr(compose_matrix[j] + ".outputMatrix", aim_matrix + ".inputMatrix")

            if j == len(aimer_trn)-1:
                cmds.connectAttr(aim_helper + ".worldMatrix", aim_matrix + ".primaryTargetMatrix")
                cmds.setAttr(aim_matrix + ".primaryInputAxisX", -1)
                cmds.setAttr(aim_matrix + ".primaryInputAxisY", 0) 
                cmds.setAttr(aim_matrix + ".primaryInputAxisZ", 0) 
            
            else:
                cmds.connectAttr(skinning_joints[j+1] + ".worldMatrix", aim_matrix + ".primaryTargetMatrix")
                cmds.setAttr(aim_matrix + ".primaryInputAxisX", 1)
                cmds.setAttr(aim_matrix + ".primaryInputAxisY", 0) 
                cmds.setAttr(aim_matrix + ".primaryInputAxisZ", 0) 
            
            cmds.connectAttr(aim + ".worldMatrix", aim_matrix + ".secondaryTargetMatrix")

            cmds.setAttr(aim_matrix + ".primaryMode", 1)
            cmds.setAttr(aim_matrix + ".secondaryMode", 1)


            cmds.setAttr(aim_matrix + ".secondaryInputAxisX", 0) 
            cmds.setAttr(aim_matrix + ".secondaryInputAxisY", 1) 
            cmds.setAttr(aim_matrix + ".secondaryInputAxisZ", 0) 

            dcp = cmds.createNode("decomposeMatrix", n=f"C_tail0{j}_DCP")
            cmds.connectAttr(aim_matrix + ".outputMatrix", dcp + ".inputMatrix")
            cmds.connectAttr(dcp + ".outputRotate", skinning_joints[j] + ".rotate")


tailModule().create_nurbs()