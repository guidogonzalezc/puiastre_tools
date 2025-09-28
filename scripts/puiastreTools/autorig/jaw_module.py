import maya.cmds as cmds
import maya.OpenMaya as om
import PyRig.utilites.export_curves as ctls
from importlib import reload
import math
reload(ctls)

class jawModule():
    def joint_selector(self, jaw):
        """
        Selects the joints of the eyebrow module.
        """
        self.joints = cmds.listRelatives(jaw, ad=True, type="joint") # Get all the joints in the hierarchy
        self.side = jaw[0].split("_")[0] # Get the side of the module
        self.jaw = jaw

        for joint in self.joints:
            if "C_jawEnd_JNT" in joint:
                self.chin = joint
            if "L_lips_JNT" in joint:
                self.l_lips = joint
            if "C_lowerLip_JNT" in joint:
                self.lowerLip = joint
            if "C_upperLip_JNT" in joint:
                self.upperLip = joint
            if  "R_lips_JNT" in joint:
                self.r_lips = joint
            
        self.nurbs_surface = "C_jaw_NRB"

        self.json = "D:/git/maya/autorig/exported_curves/edgar_facial_ctls.json"

        self.upper_linear_curve = "C_upperLipLinear_CRV" 
        self.lower_linear_curve = "C_lowerLipLinear_CRV" 



        self.main_ctl()


    def main_ctl(self):
        """
        Creates the main controller of the jaw module.
        """
        self.jaw_module = cmds.createNode("transform", name=f"{self.side}_jawModule_GRP")
        self.jaw_ctl_trn = cmds.createNode("transform", name=f"{self.side}_jawControllers_GRP")
        self.main_trn = cmds.createNode("transform", n=f"{self.side}_lipsOutSkinning_GRP")
        self.local_trn = cmds.createNode("transform", n=f"{self.side}_lipsLocalControls_GRP")

        cmds.parent(self.nurbs_surface, self.jaw_module)
        cmds.parent(self.upper_linear_curve, self.jaw_module)
        cmds.parent(self.lower_linear_curve, self.jaw_module)

        self.jaw_ctls = []
        self.jaw_ctls_grp = []
        self.chin_ctl = []
        self.chin_ctl_grp = []
        self.main_local_trn = []
        for name in ["upperJaw", "jaw", "chin"]:
            ctl, created_grp = ctls.controller_creator(f"{self.side}_{name}", self.json)
            cmds.parent(created_grp[0], self.jaw_ctl_trn)

            

            control_group = ctl.replace("_CTL", "_GRP")
            mmtx = cmds.createNode("multMatrix", name = ctl.replace("_CTL", "Relative_MMT"), ss=True)
            cmds.connectAttr(ctl + ".worldMatrix[0]", mmtx + ".matrixIn[0]")
            cmds.connectAttr(ctl.replace("_CTL", "_GRP") + ".worldInverseMatrix[0]", mmtx + ".matrixIn[1]")
            rel_transform = cmds.createNode("transform", name = ctl.replace("_CTL", "_REL"), ss=True)
            cmds.parent(rel_transform, control_group)
            cmds.delete(cmds.parentConstraint(control_group,rel_transform))
            cmds.connectAttr(mmtx + ".matrixSum", rel_transform + ".offsetParentMatrix")

            
            if name != "chin":
                cmds.matchTransform(created_grp[0], self.jaw, pos=True, rot=True)
                self.jaw_ctls.append(ctl)
                self.jaw_ctls_grp.append(created_grp)
            else:
                cmds.matchTransform(created_grp[0], self.chin, pos=True, rot=True)
                self.chin_ctl.append(ctl)
                self.chin_ctl_grp.append(created_grp)
                
            
            for attribute in [f"{ctl}.scaleX",f"{ctl}.scaleY",f"{ctl}.scaleZ",f"{ctl}.visibility"]:
                    cmds.setAttr(attribute, lock=True, keyable=False, channelBox=False)

            lcal_trn = self.local_structure(ctl)

            if name == "chin":
                cmds.parent(lcal_trn.replace("_TRN", "_GRP"), self.main_local_trn[-1])

            self.main_local_trn.append(lcal_trn)

        cmds.parentConstraint(self.main_local_trn[0], self.main_local_trn[1], self.nurbs_surface, mo=True)


        cmds.parent(self.chin_ctl_grp[0][0], self.jaw_ctls[1])
        
        cmds.addAttr(self.jaw_ctls[1], shortName="extraSep", niceName="EXTRA_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.jaw_ctls[1]+".extraSep", channelBox=True, lock=True)
        cmds.addAttr(self.jaw_ctls[1], shortName="collision", niceName="Collision",minValue=0,defaultValue=1, maxValue = 1, keyable=True)
        cmds.addAttr(self.jaw_ctls[1], shortName="sticky", niceName="Sticky Lips",minValue=0,defaultValue=0, maxValue = 1, keyable=True)
        cmds.addAttr(self.jaw_ctls[1], longName="zip", attributeType="bool", defaultValue=False, keyable=True)
        cmds.addAttr(self.jaw_ctls[1], shortName="lipsHeight", niceName="Lips Height",minValue=0,defaultValue=0.5, maxValue = 1, keyable=True)



        self.jaw_skinning_joints()

        self.jaw_colision()

    def jaw_skinning_joints(self):
        """
        Creates the skinning joints for the jaw module.
        """
        upper_jaw = cmds.duplicate(self.jaw, n="C_upperJaw_JNT", parentOnly=True)[0]
        cmds.parent(self.chin, self.jaw, upper_jaw, self.jaw_module)

        joints = [upper_jaw, self.jaw, self.chin]
        

        for i, name in enumerate(["C_upperJawSkinning_JNT", "C_jawSkinning_JNT", "C_chinSkinning_JNT"]):
            cmds.select(cl=True)
            joint = cmds.joint(n=name)
            cmds.parentConstraint(self.main_local_trn[i], joints[i], mo=True)
            cmds.parent(joint, self.main_trn)
            cmds.connectAttr(f"{joints[i]}.worldMatrix[0]", f"{joint}.offsetParentMatrix")
            




    def jaw_colision(self):

        pma = cmds.createNode("plusMinusAverage", name=f"{self.side}_jawCollision_PMA")
        cmds.setAttr(f"{pma}.operation", 2)
        self.jaw_ctls.reverse()
        for i, ctl in enumerate(self.jaw_ctls):
            name = ctl.split("_")[1]
            anm = ctl.replace("CTL", "ANM")
            mmt = cmds.createNode("multMatrix", name=f"{self.side}_{name}Collision_MMT")
            dcp = cmds.createNode("decomposeMatrix", name=f"{self.side}_{name}Collision_DCM")

            cmds.connectAttr(f"{ctl}.matrix", f"{mmt}.matrixIn[0]")
            cmds.connectAttr(f"{anm}.matrix", f"{mmt}.matrixIn[1]")

            cmds.connectAttr(f"{mmt}.matrixSum", f"{dcp}.inputMatrix")
            cmds.connectAttr(f"{dcp}.outputRotateX", f"{pma}.input1D[{i}]")

            if name == "upperJaw":
                clamp = cmds.createNode("clamp", name=f"{self.side}_{name}Collision_CLP")
                cmds.setAttr(f"{clamp}.minR", -360)
                cmds.connectAttr(f"{dcp}.outputRotateX", f"{clamp}.maxR")
        
        cmds.connectAttr(f"{pma}.output1D", f"{clamp}.inputR")
        flc = cmds.createNode("floatConstant", name=f"{self.side}_jawCollision_FLC")
        blend = cmds.createNode("blendTwoAttr", name=f"{self.side}_jawCollision_BTA")

        cmds.connectAttr(f"{flc}.outFloat", f"{blend}.input[0]")
        cmds.setAttr(f"{flc}.inFloat", 0)

        cmds.connectAttr(f"{self.jaw_ctls[0]}.collision", f"{blend}.attributesBlender")
        cmds.connectAttr(f"{clamp}.outputR", f"{blend}.input[1]")

        upper_jaw_sdk = self.jaw_ctls_grp[0][3]
        cmds.connectAttr(f"{blend}.output", f"{upper_jaw_sdk}.rotateX")

        self.lips()

    def lock_attrs(self, ctl, atts = [ "rotateX", "rotateY", "rotateZ", "scaleX", "scaleY", "scaleZ", "visibility"]):
        """
        Locks the attributes of a controller.
        """
        for att in atts:
            cmds.setAttr(f"{ctl}.{att}", lock=True, keyable=False, channelBox=False)


    def lips(self):
        """
        Creates the controllers for the lips.
        """

        self.upper_ctl, upper_created_grp = ctls.controller_creator(f"C_upperLip", self.json)
        self.lower_ctl, lower_created_grp = ctls.controller_creator(f"C_lowerLip", self.json)
        for ctl in [self.upper_ctl, self.lower_ctl]:    
            self.lock_attrs(ctl, atts = ["scaleX", "scaleY", "scaleZ", "visibility"])
        cmds.parent(upper_created_grp[0], self.jaw_ctl_trn)
        cmds.parent(lower_created_grp[0], self.jaw_ctl_trn)
        

        lips_joints = [self.upperLip, self.lowerLip]

        for i, ctl in enumerate([upper_created_grp[0], lower_created_grp[0]]):
            cmds.matchTransform(ctl, lips_joints[i], pos=True, rot=True)
 
            for attribute in [f"{ctl}.scaleX",f"{ctl}.scaleY",f"{ctl}.scaleZ",f"{ctl}.visibility"]:
                    cmds.setAttr(attribute, lock=True, keyable=False, channelBox=False)


        cmds.parentConstraint(self.jaw_ctls[0], lower_created_grp[0], mo=True)
        cmds.parentConstraint(self.jaw_ctls[1], upper_created_grp[0], mo=True)

        self.l_lip_ctl, l_lip_created_grp = ctls.controller_creator(f"L_lip", self.json)
        
        cmds.parent(l_lip_created_grp[0], self.jaw_ctl_trn)
        cmds.matchTransform(l_lip_created_grp[0], self.l_lips, pos=True, rot=True)

        mirror_trn = cmds.createNode("transform", name="R_lipsMirrorControls_GRP")
        cmds.parent(mirror_trn, self.jaw_ctl_trn)
        r_lip_grp = cmds.duplicate(l_lip_created_grp[0], n="R_lip_GRP")
        cmds.parent(r_lip_grp[0], mirror_trn)
        

        cmds.setAttr(f"{mirror_trn}.scaleX", -1)

        cmds.makeIdentity(mirror_trn, apply=True)

        self.lock_attrs(self.l_lip_ctl)
        # self.lock_attrs(r_lip_grp[0].replace("_GRP", "_CTL"))   

        self.r_lip_controllers = []


        self.r_lip_controllers.append(mirror_trn)

        for i in range(6):
            r_lip_transforms = cmds.listRelatives(self.r_lip_controllers[i], path=True, c=True)[0]
            lip_names = cmds.listRelatives(self.r_lip_controllers[i], c=True)[0]
            name = lip_names.replace("L_", "R_")
            self.r_lip_controllers.append(cmds.rename(r_lip_transforms, name))

        

        for ctl in [self.l_lip_ctl, self.r_lip_controllers[6]]:
            cmds.addAttr(ctl, shortName="extraSep", niceName="EXTRA_____", enumName="_____",attributeType="enum", keyable=True)
            cmds.setAttr(ctl+".extraSep", channelBox=True, lock=True)
            cmds.addAttr(ctl, shortName="upperToLower", niceName="UPPER <--> LOWER JAW",minValue=0,defaultValue=0.5, maxValue = 1, keyable=True)

            grp = ctl.replace("CTL", "GRP")

            constraint = cmds.parentConstraint(self.jaw_ctls[0], self.jaw_ctls[1], grp, mo=True)
            rev = cmds.createNode("reverse", name=ctl.replace("_CTL", "UpperLower_REV"))
            cmds.connectAttr(f"{ctl}.upperToLower", f"{rev}.inputX")
            cmds.connectAttr(f"{rev}.outputX", f"{constraint[0]}.w1")
            cmds.connectAttr(f"{ctl}.upperToLower", f"{constraint[0]}.w0")

        for control_name in [self.upper_ctl, self.lower_ctl, self.l_lip_ctl, self.r_lip_controllers[6]]:
            control_group = control_name.replace("_CTL", "_GRP")
            mmtx = cmds.createNode("multMatrix", name = control_name.replace("_CTL", "Relative_MMT"), ss=True)
            cmds.connectAttr(control_name + ".worldMatrix[0]", mmtx + ".matrixIn[0]")
            cmds.connectAttr(control_name.replace("_CTL", "_GRP") + ".worldInverseMatrix[0]", mmtx + ".matrixIn[1]")
            rel_transform = cmds.createNode("transform", name = control_name.replace("_CTL", "_REL"), ss=True)
            cmds.parent(rel_transform, control_group)
            cmds.delete(cmds.parentConstraint(control_group,rel_transform))
            cmds.connectAttr(mmtx + ".matrixSum", rel_transform + ".offsetParentMatrix")
        
        
        cmds.parent(self.local_trn, self.jaw_module)
        
        self.rel_trns = []
        for i, ctl in enumerate([self.upper_ctl, self.lower_ctl, self.l_lip_ctl, self.r_lip_controllers[6]]):
            rel_grp = cmds.createNode("transform", n=ctl.replace("_CTL", "Local_GRP"), p=self.local_trn)
            rel_trn = cmds.createNode("transform", n=ctl.replace("_CTL", "Local_TRN"), p=rel_grp)

            cmds.matchTransform(rel_grp, ctl)

            mmt = cmds.createNode("multMatrix", n=ctl.replace("_CTL", "Local_MMT"), ss=True)

            cmds.connectAttr(ctl + ".worldMatrix[0]", mmt + ".matrixIn[0]")
            cmds.connectAttr(ctl.replace("_CTL", "_GRP") + ".worldInverseMatrix[0]", mmt + ".matrixIn[1]")

            if i == 3:
                
                dcmp = cmds.createNode("decomposeMatrix", name=ctl.replace("_CTL", "_DCM"))
                cmds.connectAttr(mmt + ".matrixSum", dcmp + ".inputMatrix")
                
                cmds.connectAttr(dcmp + ".outputRotate", rel_trn + ".rotate")
                cmds.connectAttr(dcmp + ".outputScale", rel_trn + ".scale")

                cmds.connectAttr(dcmp + ".outputTranslateX", rel_trn + ".translateX")
                cmds.connectAttr(dcmp + ".outputTranslateZ", rel_trn + ".translateZ")

                cmds.connectAttr(dcmp + ".outputTranslateY", rel_trn + ".translateY")

            else:

                cmds.connectAttr(mmt + ".matrixSum", rel_trn + ".offsetParentMatrix")

            self.rel_trns.append(rel_trn)



        cmds.parentConstraint(self.main_local_trn[0], self.rel_trns[0].replace("_TRN", "_GRP"), mo=True)
        cmds.parentConstraint(self.main_local_trn[1], self.rel_trns[1].replace("_TRN", "_GRP"), mo=True)
        contraint_1 = cmds.parentConstraint(self.main_local_trn[1], self.main_local_trn[0], self.rel_trns[2].replace("_TRN", "_GRP"), mo=True)[0]
        contraint_2 = cmds.parentConstraint(self.main_local_trn[1], self.main_local_trn[0], self.rel_trns[3].replace("_TRN", "_GRP"), mo=True)[0]
        
        constraints = [contraint_1, contraint_2]

        for i, ctl in enumerate([self.l_lip_ctl, self.r_lip_controllers[6]]):
            rev = ctl.replace("_CTL", "UpperLower_REV")
            cmds.connectAttr(f"{rev}.outputX", f"{constraints[i]}.w1")
            cmds.connectAttr(f"{ctl}.upperToLower", f"{constraints[i]}.w0")

        self.lips_compression()

    def local_structure(self, ctl):
        rel_grp = cmds.createNode("transform", n=ctl.replace("_CTL", "Local_GRP"), p=self.local_trn)
        rel_trn = cmds.createNode("transform", n=ctl.replace("_CTL", "Local_TRN"), p=rel_grp)

        cmds.matchTransform(rel_grp, ctl)

        mmt = cmds.createNode("multMatrix", n=ctl.replace("_CTL", "Local_MMT"), ss=True)

        cmds.connectAttr(ctl + ".worldMatrix[0]", mmt + ".matrixIn[0]")
        cmds.connectAttr(ctl.replace("_CTL", "_GRP") + ".worldInverseMatrix[0]", mmt + ".matrixIn[1]")
        cmds.connectAttr(mmt + ".matrixSum", rel_trn + ".offsetParentMatrix")

        return rel_trn

    def lips_compression(self):
        """
        Creates the compression of the lips.
        """
  
        follicles = []
        for lip_ctl in [self.l_lip_ctl, self.r_lip_controllers[6]]:
            dcmp = cmds.createNode("decomposeMatrix", name=lip_ctl.replace("_CTL", "_DCM"))
            cmds.connectAttr(lip_ctl.replace("_CTL", "Local_TRN") + ".worldMatrix[0]", dcmp + ".inputMatrix")
            cpos = cmds.createNode("closestPointOnSurface", name=lip_ctl.replace("_CTL", "_CPOS"))
            cmds.connectAttr(dcmp + ".outputTranslate", cpos + ".inPosition")
            cmds.connectAttr(self.nurbs_surface + ".worldSpace[0]", cpos + ".inputSurface")
            follicle = cmds.createNode("follicle", name=lip_ctl.replace("_CTL", "Shape_FOL"))
            fol_parent = cmds.listRelatives(follicle, p=True)[0]
            cmds.connectAttr(self.nurbs_surface + ".worldSpace[0]", follicle + ".inputSurface")
            cmds.connectAttr(cpos + ".result.parameterU", follicle + ".parameterU")
            cmds.connectAttr(cpos + ".result.parameterV", follicle + ".parameterV")
            cmds.connectAttr(follicle + ".outTranslate", fol_parent + ".translate")
            cmds.connectAttr(follicle + ".outRotate", fol_parent + ".rotate")
            fol = cmds.rename(fol_parent, lip_ctl.replace("_CTL", "_FOL"))
            cmds.parent(fol, self.jaw_module)
            follicles.append(fol)

        for lips_joint in [self.l_lips, self.lowerLip, self.upperLip, self.r_lips]:
            cmds.delete(lips_joint)

        lips_joint = []
        for joint in [self.upper_ctl, self.lower_ctl]:
            cmds.select(cl=True)
            crt_joint = cmds.joint(n=joint.replace("_CTL", "_JNT"))
            cmds.parent(crt_joint, self.jaw_module)
            cmds.matchTransform(crt_joint, joint)
            lips_joint.append(crt_joint)
            cmds.parentConstraint(joint.replace("_CTL", "Local_TRN"), crt_joint, mo=True)


        for i, ctl in enumerate([self.l_lip_ctl, self.r_lip_controllers[6]]):
            cmds.select(cl=True)
            crt_joint = cmds.joint(n=ctl.replace("_CTL", "_JNT"))
            cmds.parent(crt_joint, self.jaw_module)
            cmds.matchTransform(crt_joint, ctl, pos=True)

            renamed = cmds.rename(crt_joint, crt_joint.replace("_JNT", "Upper_JNT"))
            dupe = cmds.duplicate(renamed, n=renamed.replace("Upper_JNT", "Lower_JNT"))[0]
            

            cmds.pointConstraint(follicles[i], renamed, mo=True)
            cmds.pointConstraint(follicles[i], dupe, mo=True)

            if renamed.split("_")[0] == "L":
                cmds.aimConstraint(follicles[i], renamed, wut="object", wuo=lips_joint[0], mo=True, aim=[0,0,-1], u=[1,0,0])
                cmds.aimConstraint(follicles[i], dupe, wut="object", wuo=lips_joint[1], mo=True, aim=[0,0,-1], u=[1,0,0])
            else:
                cmds.aimConstraint(follicles[i], renamed, wut="object", wuo=lips_joint[0], mo=True, aim=[0,0,-1], u=[1,0,0])
                cmds.aimConstraint(follicles[i], dupe, wut="object", wuo=lips_joint[1], mo=True, aim=[0,0,-1], u=[1,0,0])
    
            lips_joint.append(renamed)
            lips_joint.append(dupe)

        self.upper_lip_joints = [lips_joint[0], lips_joint[2], lips_joint[4]]
        self.lower_lip_joints = [lips_joint[1], lips_joint[3], lips_joint[5]]

        self.curve_skinning_projections()


        
    def curve_skinning_projections(self):
        rebuilded_upper = cmds.rebuildCurve(self.upper_linear_curve, ch=False, rpo=False, rt=0, end=1, kr=0, kep=True, kt=0, s=4, d=3, tol=0.01, n="C_upperLip_CRV")[0]
        rebuilded_lower = cmds.rebuildCurve(self.lower_linear_curve, ch=False, rpo=False, rt=0, end=1, kr=0, kep=True, kt=0, s=4, d=3, tol=0.01, n="C_lowerLip_CRV")[0]
        cmds.parent(rebuilded_upper, self.jaw_module)
        cmds.parent(rebuilded_lower, self.jaw_module)

        upper_skin = cmds.skinCluster(self.upper_lip_joints, rebuilded_upper, tsb=True, n="C_upperLip_SKN", mi=2)[0]
        lower_skin = cmds.skinCluster(self.lower_lip_joints, rebuilded_lower, tsb=True, n="C_lowerLip_SKN", mi=2)[0]

        
        for curve, skinCluster, joints in zip([rebuilded_upper, rebuilded_lower], [upper_skin, lower_skin], [self.upper_lip_joints, self.lower_lip_joints]):
            cmds.skinPercent(skinCluster, f"{curve}.cv[0]", tv=[joints[2], 1])
            cmds.skinPercent(skinCluster, f"{curve}.cv[1]", tv=[joints[2], 1])
            cmds.skinPercent(skinCluster, f"{curve}.cv[2]", tv=[(joints[2], 0.3), (joints[0], 0.7)])
            cmds.skinPercent(skinCluster, f"{curve}.cv[3]", tv=[joints[0], 1])
            cmds.skinPercent(skinCluster, f"{curve}.cv[4]", tv=[(joints[1], 0.3), (joints[0], 0.7)]) 
            cmds.skinPercent(skinCluster, f"{curve}.cv[5]", tv=[joints[1], 1])
            cmds.skinPercent(skinCluster, f"{curve}.cv[6]", tv=[joints[1], 1])


        names = ["R_upperLip01", "R_upperLip02", "R_upperLip03", "C_upperLip01", "L_upperLip03", "L_upperLip02", "L_upperLip01"]

        upper_controls = []
        upper_controls_grp = []
        self.upper_local_trn = []
        local_offset = cmds.createNode("transform", n="C_lipsUpperLocalOffset_GRP", p=self.jaw_module)

        for i, name in enumerate(names):


            ctl, created_grp = ctls.controller_creator(name, self.json)
            self.lock_attrs(ctl, atts = ["scaleX", "scaleY", "scaleZ", "visibility"])
            cmds.parent(created_grp[0], self.jaw_ctl_trn)
            control_group = ctl.replace("_CTL", "_GRP")
            if i != 3:
                parametic = 1/6 * i
                mpa = cmds.createNode("motionPath", n=f"{self.side}_lipsUpperMotionPath0{i+1}_MPA")
                cmds.connectAttr(rebuilded_upper + ".worldSpace[0]", mpa + ".geometryPath")
                cmds.setAttr(mpa + ".uValue", parametic)
                cmp = cmds.createNode("composeMatrix", n=f"{self.side}_lipsUpperMotionPath0{i+1}_CMP")
                cmds.connectAttr(mpa + ".allCoordinates", cmp + ".inputTranslate")
                dcp = cmds.createNode("decomposeMatrix", n=f"{self.side}_lipsUpperMotionPath0{i+1}_DCM")
                cmds.connectAttr(self.jaw_ctls[1] + ".matrix", dcp + ".inputMatrix")
                cmds.connectAttr(dcp + ".outputRotate", cmp + ".inputRotate")
                
                mmtx = cmds.createNode("multMatrix", name = ctl.replace("_CTL", "Relative_MMT"), ss=True)
                cmds.connectAttr(ctl + ".worldMatrix[0]", mmtx + ".matrixIn[0]")
                cmds.connectAttr(ctl.replace("_CTL", "_GRP") + ".worldInverseMatrix[0]", mmtx + ".matrixIn[1]")
                rel_transform = cmds.createNode("transform", name = ctl.replace("_CTL", "_REL"), ss=True)
                cmds.parent(rel_transform, control_group)
                cmds.delete(cmds.parentConstraint(control_group,rel_transform))
                cmds.connectAttr(mmtx + ".matrixSum", rel_transform + ".offsetParentMatrix")

                compose_value = cmds.getAttr(f"{cmp}.outputMatrix")
          
                cmds.setAttr(f"{created_grp[0]}.offsetParentMatrix", compose_value, type="matrix")

                compose_inverse_matrix = cmds.getAttr(f"{created_grp[0]}.worldInverseMatrix[0]")

                mult_matrix_offset = cmds.createNode("multMatrix", n=ctl.replace("_CTL", "Offset_MMT"), ss=True)
                cmds.connectAttr(f"{cmp}.outputMatrix", mult_matrix_offset + ".matrixIn[0]")
                # cmds.connectAttr(created_grp[0] + ".worldInverseMatrix[0]", mult_matrix_offset + ".matrixIn[1]")
                cmds.setAttr(f"{mult_matrix_offset}.matrixIn[1]", compose_inverse_matrix, type="matrix")

                cmds.connectAttr(mult_matrix_offset + ".matrixSum", created_grp[2] + ".offsetParentMatrix")
 

                lcal_trn = self.local_structure(ctl)

            
            else:
                lcal_trn = self.local_structure(ctl)

            
                mult_matrix = cmds.createNode("multMatrix", n=lcal_trn.replace("_TRN", "Offset_MMT"), ss=True)
                cmds.connectAttr(self.upper_ctl + ".worldMatrix[0]", mult_matrix + ".matrixIn[0]")   
                cmds.connectAttr(control_group + ".worldInverseMatrix[0]", mult_matrix + ".matrixIn[1]")
                cmds.connectAttr(mult_matrix + ".matrixSum", ctl + ".offsetParentMatrix")

            self.upper_local_trn.append(lcal_trn)

            upper_controls.append(ctl)
            upper_controls_grp.append(created_grp)
        
        names = ["R_lowerLip01", "R_lowerLip02", "R_lowerLip03", "C_lowerLip01", "L_lowerLip03", "L_lowerLip02", "L_lowerLip01"]

        lower_controls = []
        lower_controls_grp = []
        self.lower_local_trn = []
        local_offset = cmds.createNode("transform", n="C_lipsLowerLocalOffset_GRP", p=self.jaw_module)
        for i, name in enumerate(names):
            ctl, created_grp = ctls.controller_creator(name, self.json)
            self.lock_attrs(ctl, atts = ["scaleX", "scaleY", "scaleZ", "visibility"])
            cmds.parent(created_grp[0], self.jaw_ctl_trn)
            control_group = ctl.replace("_CTL", "_GRP")
            if i != 3:
                parametic = 1/6 * i
                mpa = cmds.createNode("motionPath", n=f"{self.side}_lipsLowerMotionPath0{i+1}_MPA")
                cmds.connectAttr(rebuilded_lower + ".worldSpace[0]", mpa + ".geometryPath")
                cmds.setAttr(mpa + ".uValue", parametic)
                # cmds.setAttr(mpa + ".fractionMode", 1)
                cmp = cmds.createNode("composeMatrix", n=f"{self.side}_lipsLowerMotionPath0{i+1}_CMP")
                cmds.connectAttr(mpa + ".allCoordinates", cmp + ".inputTranslate")
                dcp = cmds.createNode("decomposeMatrix", n=f"{self.side}_lipsLowerMotionPath0{i+1}_DCM")
                cmds.connectAttr(self.jaw_ctls[0] + ".matrix", dcp + ".inputMatrix")
                cmds.connectAttr(dcp + ".outputRotate", cmp + ".inputRotate")
                
                mmtx = cmds.createNode("multMatrix", name = ctl.replace("_CTL", "Relative_MMT"), ss=True)
                cmds.connectAttr(ctl + ".worldMatrix[0]", mmtx + ".matrixIn[0]")
                cmds.connectAttr(ctl.replace("_CTL", "_GRP") + ".worldInverseMatrix[0]", mmtx + ".matrixIn[1]")
                rel_transform = cmds.createNode("transform", name = ctl.replace("_CTL", "_REL"), ss=True)
                cmds.parent(rel_transform, control_group)
                cmds.delete(cmds.parentConstraint(control_group,rel_transform))
                cmds.connectAttr(mmtx + ".matrixSum", rel_transform + ".offsetParentMatrix")
                compose_value = cmds.getAttr(f"{cmp}.outputMatrix")
                

                cmds.setAttr(f"{created_grp[0]}.offsetParentMatrix", compose_value, type="matrix")

                compose_inverse_matrix = cmds.getAttr(f"{created_grp[0]}.worldInverseMatrix[0]")

                mult_matrix_offset = cmds.createNode("multMatrix", n=ctl.replace("_CTL", "Offset_MMT"), ss=True)
                cmds.connectAttr(f"{cmp}.outputMatrix", mult_matrix_offset + ".matrixIn[0]")
                # cmds.connectAttr(created_grp[0] + ".worldInverseMatrix[0]", mult_matrix_offset + ".matrixIn[1]")
                cmds.setAttr(f"{mult_matrix_offset}.matrixIn[1]", compose_inverse_matrix, type="matrix")

                cmds.connectAttr(mult_matrix_offset + ".matrixSum", created_grp[2] + ".offsetParentMatrix")

                lcal_trn = self.local_structure(ctl)


            
            else:
                lcal_trn = self.local_structure(ctl)

            
                mult_matrix = cmds.createNode("multMatrix", n=lcal_trn.replace("_TRN", "Offset_MMT"), ss=True)
                cmds.connectAttr(self.lower_ctl + ".worldMatrix[0]", mult_matrix + ".matrixIn[0]")   
                cmds.connectAttr(control_group + ".worldInverseMatrix[0]", mult_matrix + ".matrixIn[1]")
                cmds.connectAttr(mult_matrix + ".matrixSum", ctl + ".offsetParentMatrix")


            
            self.lower_local_trn.append(lcal_trn)

            lower_controls.append(ctl)
            lower_controls_grp.append(created_grp)

        self.dupe_upper = cmds.duplicate(rebuilded_upper, n="C_upperLipOut_CRV")[0]
        cmds.delete(self.dupe_upper, ch=True)
        self.dupe_lower = cmds.duplicate(rebuilded_lower, n="C_lowerLipOut_CRV")[0]
        cmds.delete(self.dupe_lower, ch=True)

        self.sticky_curve = cmds.duplicate(self.dupe_upper, n="C_lipsStickyCurve_CRV")[0]
        avg_curve = cmds.createNode("avgCurves", n="C_lipsAverageCurve_AVG", ss=True)

        cmds.connectAttr(f"{self.dupe_upper}.worldSpace[0]", f"{avg_curve}.inputCurve1")
        cmds.connectAttr(f"{self.dupe_lower}.worldSpace[0]", f"{avg_curve}.inputCurve2")
        cmds.setAttr(f"{avg_curve}.normalizeWeights", 0)
        cmds.setAttr(f"{avg_curve}.automaticWeight", 0)

        rev = cmds.createNode("reverse", n="C_lipsAverageCurve_REV")
        cmds.connectAttr(f"{self.jaw_ctls[0]}.lipsHeight", f"{rev}.inputX") 
        cmds.connectAttr(f"{rev}.outputX", f"{avg_curve}.weight1")
        cmds.connectAttr(f"{self.jaw_ctls[0]}.lipsHeight", f"{avg_curve}.weight2")


        cmds.connectAttr(f"{avg_curve}.outputCurve", f"{self.sticky_curve}.create", f=True)


        for curve, name in zip([self.dupe_upper, self.dupe_lower], ["upper", "lower"]):
            cvs = cmds.ls(f"{curve}.cv[*]", fl=True)
            joints = []
            for i, cv in enumerate(cvs):
                cmds.select(cl=True)
                joint = cmds.joint(n=f"C_{name}Lip{i+1:02d}_JNT")
                cmds.parent(joint, self.jaw_module)
                pos = cmds.pointPosition(cv, w=True)
                cmds.xform(joint, t=pos, ws=True)
                joints.append(joint)
                if name == "upper":
                    cmds.parentConstraint(self.upper_local_trn[i], joint, mo=False)
                else:
                    cmds.parentConstraint(self.lower_local_trn[i], joint, mo=False)
            skc = cmds.skinCluster(joints, curve, tsb=True, n=f"C_{name}LipOut_SKN", mi=2)[0]

            for i, joint in enumerate(joints):
                
                cmds.skinPercent(skc, f"{curve}.cv[{i}]", tv=[joint, 1])
        self.out_joints()
            
    def out_joints(self):
        skinning_curve = [self.dupe_upper, self.dupe_lower]
        z = -1

        cmds.addAttr(self.jaw_ctls[0], longName="secondaryControllers", attributeType="bool", defaultValue=False, keyable=True)




        for curve, name, main_ctls in zip([self.upper_linear_curve, self.lower_linear_curve], ["upper", "lower"], [self.upper_ctl, self.lower_ctl]):
            z += 1
            trn = cmds.createNode("transform", n=f"{self.side}_{name}LipOutSkinning_GRP", parent=self.main_trn)
            aim_trn_main = cmds.createNode("transform", n=f"{self.side}_{name}LipOutSkinningAim_TRN")
            cmds.parent(aim_trn_main, self.jaw_module)
            cvs = cmds.ls(f"{curve}.cv[*]", fl=True)
            joints = []

            lips_rotate_ctl, grp = ctls.controller_creator(f"{self.side}_{name}LipsRotate", self.json)
            for attr in ["tx" , "tz", "ty", "scaleX", "scaleY", "scaleZ", "visibility"]:
                cmds.setAttr(f"{lips_rotate_ctl}.{attr}", lock=True, keyable=False, channelBox=False)
            cmds.parent(grp[0], main_ctls)

            cvs = cmds.ls(f"{curve}.cv[*]", fl=True)
            center_cv_index = len(cvs) // 2  # Get the index of the center CV
            center_position = cmds.pointPosition(cvs[center_cv_index], world=True)
            cmds.xform(grp[0], t=center_position, ws=True)

            center_index = len(cvs) // 2
            rotate_percentage = [0] * len(cvs)

            for i in range(len(cvs)):
                if i < center_index:
                    rotate_percentage[i] = -i / center_index
                elif i > center_index:
                    rotate_percentage[i] = -(len(cvs) - 1 - i) / center_index
                else:
                    rotate_percentage[i] = -1


            third_controllers_grp = cmds.createNode("transform", n=f"{self.side}_{name}LipOutThirdControls_GRP", p=self.jaw_ctl_trn)
            cmds.connectAttr(f"{self.jaw_ctls[0]}.secondaryControllers", f"{third_controllers_grp}.visibility") 

            for i, cv in enumerate(cvs):
                
                closestPointOnCurve = cmds.createNode("nearestPointOnCurve", n=f"{self.side}_{name}LipOutSkinningCPOS{i:02d}_CPC")
                cmds.connectAttr(f"{skinning_curve[z]}.worldSpace[0]", f"{closestPointOnCurve}.inputCurve")      
                position = cmds.pointPosition(cv, w=True)
                cmds.setAttr(f"{closestPointOnCurve}.inPosition", position[0], position[1], position[2])
                parameter = cmds.getAttr(f"{closestPointOnCurve}.parameter")

                cmds.delete(closestPointOnCurve)          





                cmds.select(cl=True)
                pos = cmds.pointPosition(cv, w=True)
                if abs(pos[0]) <= 0.001:
                    side = "C"
                    number = 1
                elif pos[0] < -0.001:
                    side = "R"
                    number = i + 1
                elif pos[0] > 0.001:
                    side = "L"
                    number = (len(cvs) - i)

                    
                joint = cmds.joint(n=f"{side}_lips{name}SkinningJoints{number:02d}_JNT")
                cmds.parent(joint, trn)
                # cmds.xform(joint, t=pos, ws=True)

                aim_trn = cmds.createNode("transform", n=f"C_{name}Lips_0{i}_TRN", p=aim_trn_main)

                mpa = cmds.createNode("motionPath", n=f"{self.side}_{name}Lips_0{i}_MPA")
                cmds.setAttr(mpa + ".uValue", parameter)
                cmds.connectAttr(skinning_curve[z] + ".worldSpace[0]", mpa + ".geometryPath")
                cmp = cmds.createNode("composeMatrix", n=f"{self.side}_{name}Lips_0{i}_CMP")

                cmds.connectAttr(mpa + ".allCoordinates", cmp + ".inputTranslate")
                amx = cmds.createNode("aimMatrix", n=f"{self.side}_{name}Lips_0{i}_AMX")
                cmds.connectAttr(cmp + ".outputMatrix", amx + ".inputMatrix")
                cmds.connectAttr(self.main_local_trn[1] + ".worldMatrix[0]", amx + ".primaryTargetMatrix")
                cmds.setAttr(amx + ".primaryInputAxis", 0, 1, 0)
                cmds.setAttr(amx + ".primaryMode", 1)
                cmds.setAttr(amx + ".primaryTargetVector", 0, 1, 0)
                cmds.setAttr(amx + ".secondaryInputAxis", 0, 0, 1)
                cmds.setAttr(amx + ".secondaryMode", 1)
                cmds.setAttr(amx + ".secondaryTargetVector", 0, 0, 1)

                mpa_sticky = cmds.createNode("motionPath", n=f"{self.side}_{name}Lips_0{i}Sticky_MPA")
                cmds.setAttr(mpa_sticky + ".uValue", parameter)
                cmds.connectAttr(self.sticky_curve+ ".worldSpace[0]", mpa_sticky + ".geometryPath")
                cmp_sticky = cmds.createNode("composeMatrix", n=f"{self.side}_{name}Lips_0{i}Sticky_CMP")

                cmds.connectAttr(mpa_sticky + ".allCoordinates", cmp_sticky + ".inputTranslate")
                amx_sticky = cmds.createNode("aimMatrix", n=f"{self.side}_{name}Lips_0{i}Sticky_AMX")
                cmds.connectAttr(cmp_sticky + ".outputMatrix", amx_sticky + ".inputMatrix")
                cmds.connectAttr(self.main_local_trn[1] + ".worldMatrix[0]", amx_sticky + ".primaryTargetMatrix")
                cmds.setAttr(amx_sticky + ".primaryInputAxis", 0, 1, 0)
                cmds.setAttr(amx_sticky + ".primaryMode", 1)
                cmds.setAttr(amx_sticky + ".primaryTargetVector", 0, 1, 0)
                cmds.setAttr(amx_sticky + ".secondaryInputAxis", 0, 0, 1)
                cmds.setAttr(amx_sticky + ".secondaryMode", 1)
                cmds.setAttr(amx_sticky + ".secondaryTargetVector", 0, 0, 1)

                wt_add = cmds.createNode("wtAddMatrix", n=f"{self.side}_{name}Lips_0{i}Sticky_WTAM")
                cmds.connectAttr(amx_sticky + ".outputMatrix", wt_add + ".wtMatrix[0].matrixIn")
                cmds.connectAttr(amx + ".outputMatrix", wt_add + ".wtMatrix[1].matrixIn")

                total_cvs = len(cvs)
                center_index = total_cvs // 2

                if i < center_index:
                    normalized_index = i / float(center_index)
                    start = normalized_index * 0.9
                    end = min(start + 0.2, 1.0)


                    remap_value = cmds.createNode("remapValue", n=f"{side}_{name}Lips_0{number}Sticky_RMV", ss=True)
                    cmds.connectAttr(f"{self.jaw_ctls[0]}.sticky", f"{remap_value}.inputValue")
                    cmds.setAttr(remap_value + ".value[0].value_Position", start)
                    cmds.setAttr(remap_value + ".value[0].value_FloatValue", 0)
                    cmds.setAttr(remap_value + ".value[1].value_Position", end)
                    cmds.setAttr(remap_value + ".value[1].value_FloatValue", 1)
                elif i > center_index:
                    remap_value = f"R_{name}Lips_0{number}Sticky_RMV"
                else:
                    normalized_index = 1.0 
                    start = normalized_index * 0.9
                    end = min(start + 0.2, 1.0)


                    remap_value = cmds.createNode("remapValue", n=f"{side}_{name}Lips_0{number}Sticky_RMV", ss=True)
                    cmds.connectAttr(f"{self.jaw_ctls[0]}.sticky", f"{remap_value}.inputValue")
                    cmds.setAttr(remap_value + ".value[0].value_Position", start)
                    cmds.setAttr(remap_value + ".value[0].value_FloatValue", 0)
                    cmds.setAttr(remap_value + ".value[1].value_Position", end)
                    cmds.setAttr(remap_value + ".value[1].value_FloatValue", 1)
                


                choice = cmds.createNode("choice", n=f"{self.side}_{name}Lips_0{i}Sticky_CHO")
                cmds.connectAttr(f"{remap_value}.outValue", f"{choice}.input[1]")
                cmds.connectAttr(f"{self.jaw_ctls[0]}.sticky", f"{choice}.input[0]")
                cmds.connectAttr(f"{self.jaw_ctls[0]}.zip", f"{choice}.selector")




                cmds.connectAttr(f"{choice}.output", f"{wt_add}.wtMatrix[0].weightIn")
                rev_sticky = cmds.createNode("reverse", n=f"{self.side}_{name}Lips_0{i}Sticky_REV")
                cmds.connectAttr(f"{choice}.output", f"{rev_sticky}.inputX")
                cmds.connectAttr(f"{rev_sticky}.outputX", f"{wt_add}.wtMatrix[1].weightIn")


                out_matrix = cmds.getAttr(amx + ".outputMatrix")

                cmds.setAttr(aim_trn + ".offsetParentMatrix", out_matrix, type="matrix")


                ctl, ctl_grp = ctls.controller_creator(f"{side}_{name}LipOutSkinning{number:02d}", self.json)
                cmds.parent(ctl_grp[0], third_controllers_grp)  
                cmds.setAttr(ctl_grp[0] + ".offsetParentMatrix", out_matrix, type="matrix")

                multiply_divide = cmds.createNode("multiplyDivide", n=ctl.replace("_CTL", "_MDN"), ss=True)
                cmds.setAttr(multiply_divide + ".input2X", rotate_percentage[i])
                cmds.setAttr(multiply_divide + ".input2Y", rotate_percentage[i])
                cmds.setAttr(multiply_divide + ".input2Z", rotate_percentage[i])
                cmds.connectAttr(lips_rotate_ctl + ".rotate", multiply_divide + ".input1")

                cmds.connectAttr(multiply_divide + ".output", ctl_grp[3] + ".rotate")


                mult_matrix = cmds.createNode("multMatrix", n=ctl.replace("_CTL", "Offset_MMT"), ss=True)
                cmds.connectAttr(wt_add + ".matrixSum", mult_matrix + ".matrixIn[0]")
                cmds.connectAttr(aim_trn + ".worldInverseMatrix[0]", mult_matrix + ".matrixIn[1]")
                cmds.connectAttr(mult_matrix + ".matrixSum", ctl_grp[2] + ".offsetParentMatrix")

                local_trn = self.local_structure(ctl)
                cmds.connectAttr(local_trn + ".worldMatrix[0]", joint + ".offsetParentMatrix")


                joints.append(joint)
    
        for jnt in cmds.ls(type="joint"):
            if "L_" in jnt:
                cmds.setAttr(jnt + ".side", 1)
            if "R_" in jnt:
                cmds.setAttr(jnt + ".side", 2)
            if "C_" in jnt:
                cmds.setAttr(jnt + ".side", 0)
            cmds.setAttr(jnt + ".type", 18)
            cmds.setAttr(jnt + ".otherType", jnt.split("_")[1], type= "string")
            cmds.setAttr(jnt + ".radius", 0.1)  




jaw = jawModule()
jaw.joint_selector("C_jaw_JNT")


