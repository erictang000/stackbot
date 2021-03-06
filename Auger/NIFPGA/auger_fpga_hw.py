from ScopeFoundry import HardwareComponent
from Auger.NIFPGA.ext_trig_auger_fpga import ExtTrigAugerFPGA
import numpy as np

class AugerFPGA_HW(HardwareComponent):
    
    name = 'auger_fpga'
    tick = 25e-9 #FPGA cycle
    
    def setup(self):
        
        self.settings.New('trigger_mode', dtype=str, initial='off', choices=('off', 'pxi', 'dio', 'int'))
        self.settings.New('overflow', dtype=bool, ro=True)
        self.settings.New('int_trig_sample_count', dtype=int, initial=0, vmin=0) # zero --> continuous
        self.settings.New('int_trig_sample_period', dtype=int, initial=40000, vmin=0, unit='cycles_25ns') 
        self.settings.New('period', dtype=float, initial=1e-3, vmin=0, unit='s', si=True) 

        self.NUM_CHANS = 10

    def connect(self):
        
        self.log.debug('connecting auger_fpga')
        self.ext_trig_dev = ExtTrigAugerFPGA(debug=self.settings['debug_mode'])
        
        self.fpga = self.ext_trig_dev.FPGA
        
        self.fpga.reset()
        self.fpga.run()
        
        self.settings.trigger_mode.connect_to_hardware(
            read_func =self.ext_trig_dev.read_triggerMode,
            write_func=self.ext_trig_dev.write_triggerMode
            )
        
        self.settings.overflow.connect_to_hardware(
            read_func=self.ext_trig_dev.read_overflow
            )
        
        self.settings.int_trig_sample_count.connect_to_hardware(
            read_func=self.ext_trig_dev.read_sampleCount,
            write_func=self.ext_trig_dev.write_sampleCount
            )

        self.settings.int_trig_sample_period.connect_to_hardware(
            write_func=self.ext_trig_dev.write_samplePeriod,
            read_func=self.ext_trig_dev.read_samplePeriod
            )

        #self.settings.period.connect_to_hardware(
        #    write_func=self.write_period,
        #    read_func=self.read_period
        #    )
        self.settings.int_trig_sample_period.add_listener(self.on_new_int_trig_sample_period)
        self.settings.period.add_listener(self.on_new_period)

        #self.ext_trig_dev.write_triggerMode(self.settings['trigger_mode'])
        self.settings.trigger_mode.write_to_hardware()
        self.settings.int_trig_sample_count.write_to_hardware()
        self.settings.int_trig_sample_period.write_to_hardware()

        self.read_from_hardware()
        
    def disconnect(self):
        
        self.settings.disconnect_all_from_hardware()
        
        if hasattr(self, 'fpga'):
            self.ext_trig_dev.write_triggerMode('off')
            self.ext_trig_dev.flush_fifo()
            self.fpga.close()
            del self.ext_trig_dev
    
#     def read_period(self):
#         return self.tick * self.settings.int_trig_sample_period.read_from_hardware()
#     
#     def write_period(self, period = 0.001):
#         tick_count = int( max( 5, period / self.tick ))
#         self.settings.int_trig_sample_period.update_value(tick_count)
#         #self.ext_trig_dev.write_samplePeriod(tick_count)
#     
    def on_new_int_trig_sample_period(self):
        #self.settings.period.read_from_hardware()
        self.settings['period'] =  self.tick * self.settings['int_trig_sample_period']
        
    def on_new_period(self):
        tick_count = int( max( 5, self.settings['period'] / self.tick ))
        self.settings['int_trig_sample_period'] =  tick_count
    
    def flush_fifo(self):
        self.ext_trig_dev.flush_fifo()
    
    def read_fifo(self, n_transfers=-1, timeout = 0, return_remaining = False):
        """
        if n_transfers < 0: read all available transfer blocks 
        defaults to read all
        """
        if n_transfers < 0:
            n_transfers = self.ext_trig_dev.read_num_transfers_in_fifo()
            
        return self.ext_trig_dev.read_fifo_parse(n_transfers = n_transfers, timeout=timeout, return_remaining=return_remaining)
    
    #========= Measurement helper functions
    
    def setup_single_clock_mode(self, dwell = 0.05, delay_fraction = 0):
        '''
        sets internal timer to record counts for dwell*(1+delay_fraction) seconds, 
        leading delay_fraction data is discarded, to allow for measurement to settle after
        changing conditions. delay_fraction resolution 1% of dwell
        '''
            #flush fifo buffer 
        self.settings['trigger_mode'] = 'off' 
        self.flush_fifo()
        
            #calculate period and block sizes
        self.settings['period']=0.01 * dwell
        self.sample_skip = int(abs(delay_fraction)*100)
        if self.sample_skip == 0 and delay_fraction != 0:
            self.sample_skip = 1    #non-zero delay rounded up to 1%        

        self.sample_block = 100+self.sample_skip
        self.timeout = 2.0*dwell
            #restart free run counter
        self.settings['int_trig_sample_count'] = 0 
        self.settings['trigger_mode'] = 'int'

    def get_single_value(self,flush=False):
        '''
        waits for data on call, if too much data is present, flush fifo and repeat
        keeps async processes consistent
        '''
        if flush:
            self.flush_fifo()            
        remaining, buf_reshaped = self.read_fifo(n_transfers = self.sample_block,timeout = self.timeout, return_remaining=True)                
        if remaining > 0:
            #print( "samples remaining at pixel {}, resyncing".format( remaining))
            self.flush_fifo()
            remaining, buf_reshaped = self.read_fifo(n_transfers = self.sample_block,timeout = self.timeout, return_remaining=True)                
            #print( "{} samples remaining after resync".format( remaining))

        buf_reshaped = buf_reshaped[self.sample_skip:] #discard first samples, transient
        data = np.sum(buf_reshaped,axis=0)
        return np.sum(data[0:6]) #sum 7 Auger detector channels return single value

