import maya.cmds as cmds
import ctl_create_circle as c
from importlib import reload
reload(c)


class TailModule:
    def tail_import(self, guides):
        
        self.tail_jnts = cmds.listRelatives(guides[0], allDescendents=True)

    def matrix_constraint(self, driver, driven):
        pass
    
    def controller_setup(self, guides):
        
        circle = c.ControllerCreation().variable
        
        self.controllers = []
        self.grps = []
        for i, jnt in enumerate(self.tail_jnts):
            tail_ctl, tail_grp = circle(guides.split("_")[0], f"tail0{i}", 3)
            cmds.matchTransform(tail_grp[0], jnt)
            if i != 0:
                cmds.parent(tail_grp[0], self.controllers[-1])
            self.controllers.append(tail_ctl)
            self.grps.append(tail_grp)
            
        

    