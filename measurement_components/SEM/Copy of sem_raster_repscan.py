'''
Created on Feb 4, 2015

@author: NIuser
'''

from measurement_components.measurement import Measurement
import time
import numpy as np

class SemRasterRepScan(Measurement):

    name = "sem_raster_rep_scan"
    
    def setup(self):        
        self.display_update_period = 0.050 #seconds

        # Created logged quantities
        self.points = self.add_logged_quantity('points', initial=1024,
                                                   dtype=int,
                                                   ro=False,
                                                   vmin=1,
                                                   vmax=1e6,
                                                   unit='pixels')

        self.lines = self.add_logged_quantity('lines', initial=1024,
                                                   dtype=int,
                                                   ro=False,
                                                   vmin=1,
                                                   vmax=1e6,
                                                   unit='pixels')



        lq_params = dict(  dtype=float, ro=False,
                           initial = 0,
                           vmin=-50,
                           vmax=50,
                           unit='%')
        self.xoffset = self.add_logged_quantity('xoffset', **lq_params)
        self.yoffset = self.add_logged_quantity('yoffset', **lq_params)

        lq_params = dict(  dtype=float, ro=False,
                           initial = 100,
                           vmin=-100,
                           vmax=100,
                           unit='%')        
        self.xsize = self.add_logged_quantity("xsize", **lq_params)
        self.ysize = self.add_logged_quantity("ysize", **lq_params)
        
        self.angle = self.add_logged_quantity("angle", dtype=float, ro=False, initial=0, vmin=-180, vmax=180, unit="deg")
        
        
        self.sample_rate = self.add_logged_quantity("sample_rate", dtype=float, 
                                                    ro=False, 
                                                    initial=2e6, 
                                                    vmin=1, 
                                                    vmax=2e6,
                                                    unit='Hz')
        
        self.output_rate = self.add_logged_quantity("output_rate", dtype=float, 
                                                    ro=True, 
                                                    initial=5e5, 
                                                    vmin=1, 
                                                    vmax=2e6,
                                                    unit='Hz')
        
        self.sample_per_point = self.add_logged_quantity("sample_per_point", dtype=int, 
                                                    ro=False, 
                                                    initial=1, 
                                                    vmin=1, 
                                                    vmax=100,
                                                    unit='samples')
        
        self.continuous_scan = self.add_logged_quantity("continuous_scan", dtype=int, 
                                                        ro=False, 
                                                        initial=0, 
                                                        vmin=0, 
                                                        vmax=1, 
                                                        unit='',
                                                        choices=[('Off',0),('On',1)])
        self.save_file = self.add_logged_quantity("save_file", dtype=int, 
                                                        ro=False, 
                                                        initial=0, 
                                                        vmin=0, 
                                                        vmax=1, 
                                                        unit='',
                                                        choices=[('Off',0),('On',1)])
        
        #connect events
        self.gui.ui.sem_raster_repscan_start_pushButton.clicked.connect(self.start)
        self.gui.ui.sem_raster_repscan_stop_pushButton.clicked.connect(self.interrupt)
        
        self.points.connect_bidir_to_widget(self.gui.ui.points_doubleSpinBox)
        self.lines.connect_bidir_to_widget(self.gui.ui.lines_doubleSpinBox)
        self.xoffset.connect_bidir_to_widget(self.gui.ui.xoffset_doubleSpinBox)
        self.yoffset.connect_bidir_to_widget(self.gui.ui.yoffset_doubleSpinBox)
        self.xsize.connect_bidir_to_widget(self.gui.ui.xsize_doubleSpinBox)
        self.ysize.connect_bidir_to_widget(self.gui.ui.ysize_doubleSpinBox)
        self.angle.connect_bidir_to_widget(self.gui.ui.angle_doubleSpinBox)
        self.sample_rate.connect_bidir_to_widget(self.gui.ui.sample_rate_doubleSpinBox)
        self.sample_per_point.connect_bidir_to_widget(self.gui.ui.sample_per_point_doubleSpinBox)
        self.save_file.connect_bidir_to_widget(self.gui.ui.save_file_comboBox)
        
    def setup_figure(self):
        self.fig = self.gui.add_figure('sem_raster', self.gui.ui.sem_raster_plot_widget)


    def _run(self):
        from equipment.SEM.raster_generator import  RasterGenerator
        from equipment.NI_Daq import Sync
        from datetime import datetime

        self.raster_gen = RasterGenerator(points=self.points.val, lines=self.lines.val, 
                                          xoffset=self.xoffset.val, yoffset=self.yoffset.val,
                                          xsize=self.xsize.val, ysize=self.ysize.val,
                                          angle=self.angle.val)
        
        # need to update values based on clipping
        
        self.xy_raster_volts = self.raster_gen.data()
        self.num_pixels = self.raster_gen.count()
        self.num_samples= self.num_pixels *self.sample_per_point.val
       
        #setup tasks
        #while self.continuous_scan.val==1:
        self.sync_analog_io = Sync('X-6368/ao0:1', 'X-6368/ai1:3')
        '''
        from sample per point and sample rate, calculate the output(scan rate)
        '''
        self.output_rate.val=self.sample_rate.val/self.sample_per_point.val
        
        #self.sync_analog_io.setup(rate_out=self.sample_rate.val, count_out=self.num_pixels, 
        #                          rate_in=self.sample_rate.val, count_in=self.num_pixels )
        self.sync_analog_io.setup(self.output_rate.val, int(self.num_pixels), self.sample_rate.val, int(self.num_samples),is_finite=True)
        from equipment.image_io import ChannelInfo
        from equipment.image_io import Collection
        
        self.continuous_scan.val=1
        
        if self.save_file.val==1:
            ch_infos=[ChannelInfo('image',(self.points.val,self.lines.val))]
            
            t=datetime.now()
            tname=t.strftime('%Y-%m-%d-%H-%M-%S')
            self.collection=Collection(name=tname,
                                  create=True,
                                  initial_size=100,
                                  expansion_size=100,
                                  channel_infos=ch_infos)
            self.collection.save_measurement_component(self.dict_logged_quantity_val(self.logged_quantities), self.dict_logged_quantity_unit(self.logged_quantities))
            self.sem_remcon=self.gui.sem_remcon
            self.collection.save_hardware_component('sem_remcon', self.dict_logged_quantity_val(self.sem_remcon.logged_quantities), self.dict_logged_quantity_unit(self.sem_remcon.logged_quantities))
        
        
        while self.continuous_scan.val==1:
            if self.interrupt_measurement_called:
                break
            self.sync_analog_io.out_data(self.xy_raster_volts)
            self.sync_analog_io.start()
            self.adc_data = self.sync_analog_io.read_buffer(timeout=10)
            
            '''
            obtain input signal, average copies of samples and reshape it for image display
            '''
            in3 = self.adc_data[::3]
            print 'numpix'+str(self.num_pixels)
            print 'original'+ str(in3.shape)
            if self.sample_per_point.val>1:
                in3=in3.reshape((self.num_pixels,self.sample_per_point.val))
                print 'oversampling'+str(in3.shape)
                in3= in3.mean(axis=1)
                print 'averaged'+str(in3.shape)
            #in1 = self.adc_data[1::3]
            #in2 = self.adc_data[2::3]
            #out1 = self.xy_raster_volts[::2]
            #out2 = self.xy_raster_volts[1::2]

            #out1 = out1.reshape(self.raster_gen.shape())
            #out2 = out2.reshape(self.raster_gen.shape())
            #in1 = in1.reshape(self.raster_gen.shape())
            #in2 = in2.reshape(self.raster_gen.shape())
            in3 = in3.reshape(self.raster_gen.shape())
            if self.save_file.val==1:
                self.collection.update({'image':in3})
            self.sem_image = in3
            self.sync_analog_io.stop()
        if self.save_file.val==1:
            self.collection.close()
        
    def update_display(self):        
        #print "updating figure"
        #self.fig.clf()
        
        if not hasattr(self,'ax'):
            self.ax = self.fig.add_subplot(111)
            
        if not hasattr(self, 'img'):
            self.img = self.ax.imshow(self.sem_image)

        self.img.set_data(self.sem_image)

        self.fig.canvas.draw()
    
    def get_hardware_logged_quantity(self,hardware):
        return hardware.logged_quantities
    
    def list_hardware_components(self):
        return self.gui.hardware_components
    
    def dict_logged_quantity_val(self,logged_quantities):
        val_dict=dict()
        for name in self.logged_quantities:
            val_dict[name]=self.logged_quantities[name].val
        return val_dict
    
    def dict_logged_quantity_unit(self,logged_quantities):
        val_dict=dict()
        for name in self.logged_quantities:
            val_dict[name]=self.logged_quantities[name].unit
        return val_dict

# if __name__=='__main__':
#     from base_gui import BaseMicroscopeGUI
#    
#     scan=SemRasterRepScan(gui)
#     resp=scan.get_measurement_logged_quantity()
#     print(resp)