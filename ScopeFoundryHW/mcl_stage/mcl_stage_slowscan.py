from __future__ import division, print_function
#import numpy as np
from ScopeFoundry.scanning import BaseRaster2DSlowScan, BaseRaster2DFrameSlowScan
#from ScopeFoundry import Measurement, LQRange
#import time

class MCLStage2DSlowScan(BaseRaster2DSlowScan):
    
    name = "MCLStage2DSlowScan"
    def __init__(self, app):
        BaseRaster2DSlowScan.__init__(self, app, h_limits=(0,75), v_limits=(0,75), h_unit="um", v_unit="um")        
    
    def setup(self):
        BaseRaster2DSlowScan.setup(self)
        
        self.settings.New("h_axis", initial="X", dtype=str, choices=("X", "Y", "Z"))
        self.settings.New("v_axis", initial="Y", dtype=str, choices=("X", "Y", "Z"))
        
        self.ax_map = dict(X=0, Y=1, Z=2)
        #Hardware
        self.stage = self.app.hardware.mcl_xyz_stage

    def move_position_start(self, h,v):
        #self.stage.y_position.update_value(x)
        #self.stage.y_position.update_value(y)
        
        S = self.settings
        
        coords = [None, None, None]
        coords[self.ax_map(S['h_axis'])] = h
        coords[self.ax_map(S['v_axis'])] = v
        
        #self.stage.move_pos_slow(x,y,None)
        self.stage.move_pos_slow(*coords)
        self.stage.settings.x_position.read_from_hardware()
        self.stage.settings.y_position.read_from_hardware()
        self.stage.settings.z_position.read_from_hardware()
    
    def move_position_slow(self, h,v, dh,dv):
        self.move_position_start(h, v)

    def move_position_fast(self,  h,v, dh,dv):
        #self.stage.x_position.update_value(x)
        S = self.settings        
        coords = [None, None, None]
        coords[self.ax_map(S['h_axis'])] = h
        coords[self.ax_map(S['v_axis'])] = v
        self.stage.move_pos_fast(*coords)
        #self.stage.move_pos_fast(x, y, None)
        #self.current_stage_pos_arrow.setPos(x, y)
        #self.stage.settings.x_position.read_from_hardware()
        #self.stage.settings.y_position.read_from_hardware()
        
    
class MCLStage2DFrameSlowScan(BaseRaster2DFrameSlowScan):
    
    name = "MCLStage2DFrameSlowScan"
    
    def __init__(self, app):
        BaseRaster2DFrameSlowScan.__init__(self, app, h_limits=(0,75), v_limits=(0,75), h_unit="um", v_unit="um")        
    
    def setup(self):
        MCLStage2DSlowScan.setup(self)

    def move_position_start(self, h,v):
        MCLStage2DSlowScan.move_position_start(self, h, v)
    
    def move_position_slow(self, h,v, dh,dv):
        MCLStage2DSlowScan.move_position_slow(self, h,v, dh,dv)
        
    def move_position_fast(self,  h,v, dh,dv):
        MCLStage2DSlowScan.move_position_fast(self,  h,v, dh,dv)
        
        
class MCLStage3DStackSlowScan(MCLStage2DFrameSlowScan):
    
    def setup(self):
        MCLStage2DFrameSlowScan.setup(self)
        
        self.settings.New("stack_axis", initial="Z", dtype=str, choices=("X", "Y", "Z"))
        self.settings.New_Range('stack', dtype=float)
        
        self.settings.stack_num.add_listener(self.settings.n_frames.update_value, int)
        
    def on_new_frame(self, frame_i):
        S = self.settings
        stack_range = S.ranges['stack']
        
        stack_pos_i = stack_range.array[frame_i]
        coords = [None, None, None]
        coords[self.ax_map(S['stack_axis'])] = stack_pos_i
        
        self.stage.move_pos_slow(*coords)
        self.stage.settings.x_position.read_from_hardware()
        self.stage.settings.y_position.read_from_hardware()
        self.stage.settings.z_position.read_from_hardware()
        


