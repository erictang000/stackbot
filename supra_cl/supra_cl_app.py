from ScopeFoundry import BaseMicroscopeApp


import logging
logging.basicConfig(level='DEBUG')
logging.getLogger('').setLevel(logging.DEBUG)
logging.getLogger("ipykernel").setLevel(logging.WARNING)
logging.getLogger('PyQt4').setLevel(logging.WARNING)
logging.getLogger('PyQt5').setLevel(logging.WARNING)
logging.getLogger('traitlets').setLevel(logging.WARNING)

logging.getLogger('LoggedQuantity').setLevel(logging.WARNING)


class SupraCLApp(BaseMicroscopeApp):
    
    name = 'supra_cl'
    
    def setup(self):
        
        # import pyqtgraph as pg
        #pg.setConfigOption('background', 'w')
        #pg.setConfigOption('foreground', 'k')

        
        from Auger.sem_sync_raster_hardware import SemSyncRasterDAQ
        self.add_hardware(SemSyncRasterDAQ(self))

        from Auger.hardware.remcon32_hw import SEM_Remcon_HW
        self.add_hardware(SEM_Remcon_HW(self))
        
        from Auger.sem_sync_raster_measure import SemSyncRasterScan
        self.add_measurement(SemSyncRasterScan(self))
        
        from supra_cl.sem_sync_raster_quad_measure import SemSyncRasterScanQuadView
        self.add_measurement(SemSyncRasterScanQuadView(self))
        
        from ScopeFoundryHW.andor_camera import AndorCCDHW, AndorCCDReadoutMeasure
        self.add_hardware(AndorCCDHW(self))
        self.add_measurement(AndorCCDReadoutMeasure(self))

        from ScopeFoundryHW.acton_spec import ActonSpectrometerHW
        self.add_hardware(ActonSpectrometerHW(self))

        #self.hardware['xbox_controller'].settings.get_lq('connected').update_value(True)

        self.settings_load_ini('supra_cl_defaults.ini')

        self.ui.show()

        
if __name__ == '__main__':
    app = SupraCLApp([])
    app.exec_()
