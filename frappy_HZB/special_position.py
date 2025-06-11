
import re
import uuid

from frappy.core import BUSY, IDLE, Command, Drivable, IntRange, \
    Parameter, Readable, StructOf
from frappy.datatypes import ArrayOf, EnumType, FloatRange, StatusType, \
    StringType
from frappy.errors import ImpossibleError, IsBusyError
from frappy.lib.enum import Enum
from frappy.modules import Attached

from samplechanger_sm import SamplechangerSM

nsamples = 12

EMPTY_SLOT = ""





class Special_Position(Drivable):
    
    Status = Enum(Drivable.Status,
                  DISABLED = StatusType.DISABLED,
                  PREPARING = StatusType.PREPARING,
                  HOLDING_SAMPLE = 101, 
                  MOUNTING=301,
                  UNMOUNTING = 302,
                  UNLOADING = 304,
                  PAUSED = 305,
                  UNKNOWN = 401,
                  STOPPED = 402,
                  LOCAL_CONTROL = 403,
                  LOCKED = 404 
                  )  #: status codes

    status = Parameter(datatype=StatusType(Status))  
    
    
    a_hardware = Attached(mandatory = True)
    a_storage   = Attached(mandatory = True)
    
    value = Parameter("ID of the sample currently present at " +
                      "the position ('' means that the Position is empty)",
                    datatype=StringType(maxchars=50),
                    readonly = True,
                    default = "")
    
    target = Parameter("ID of the sample that should be moved to the position ",
                       datatype=StringType(maxchars = 50),
                       default = "") 
    
    next_sample = Parameter("ID of the next sample that should be moved to the position ",
                            datatype=StringType(maxchars = 50),
                            readonly = True,
                            export = False,
                            default = "")
    
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.a_hardware.sm.set_special_pos(self)
        self.callbacks = [
            ('ok','mount',self.mount_ok_callback),
            ('ok','unmount',self.unmount_ok_callback),
            ('ok','unmount_switch',self.unmount_ok_callback),
            ('error','mount',self.mount_error_callback),
            ('error','unmount',self.unmount_error_callback),
            ('error','unmount_switch',self.unmount_error_callback),
        ]
        
        self.a_hardware.robo_server.add_callbacks(self.callbacks)
        
    def read_value(self):
        return self.value
    
    def read_target(self):  
        return self.target
    
    def write_target(self,target):               

        

        
        if not target:      
            ### Unmount:
            return self._unmount("unmount")
        else:                   
           ### Mount: 
            if target == self.value:
               return target
           
            # just mount the desired Sample
            if self.a_hardware.sm.current_state == SamplechangerSM.home:
                return self._mount("mount",target)
        
           # unmount current sample and set target as nex sample to be mounted
            self.next_sample = target        
  
            if self.a_hardware.sm.current_state == SamplechangerSM.home_mounted:
                self._unmount("mount")
    
    def mount_error_callback(self,error_message= None):
        self.a_hardware.error_occured(error_message)
        self.read_status()
    
    
    def mount_ok_callback(self):
        # Robot successfully mounting the sample
        print("mount ok")
        self.value = self.target
        self.read_target()
        self.read_value()
    
    def unmount_error_callback(self,error_message= None):
        self.a_hardware.error_occured(error_message)
        self.read_status()
    
    def unmount_ok_callback(self):
        # Robot successfully unmounted the sample
        print("unmount ok")
        self.value = ""
        self.read_value()
    
    
       
    def _mount(self,sm_event,target):
        """Mount Sample to Robot arm"""
        
        assert(target != "")
        
        curr_state = self.a_hardware.sm.current_state   
        
        self.log.info(f"requested sample: {target} to be mounted")      
        
        #check if curr_state is in a list of states where mounting is possible
        if curr_state not in [SamplechangerSM.home, SamplechangerSM.home_switch, SamplechangerSM.home_mounted]:        
            raise ImpossibleError('Robot is currently not in home position, cannot mount sample')

        # check if sample is present in Storage
        if self.a_storage.mag.get_index(target) == None:
            raise ImpossibleError('no sample with ID: ' +str(target)+' in storage! please, check sample objects stored in storage')
              
        slot = self.a_storage.mag.get_index(target) +1
     
        # Run Robot script to mount actual Sample        
        prog_name = 'messin'+ str(slot) + '.urp'
        
        assert(re.match(r'messin\d+\.urp',prog_name) )
        
        self.a_hardware.run_program(prog_name,sm_event)
 
        self.status = MOUNTING , "Mounting Sample: " + str(target)
        
        self.target = target
        

        
        self.read_status()
        
        self.a_storage.mag.set_generator_index(target)
        
        next_sample = self.a_storage.mag.get_next_sample()

        
        if next_sample == None:
            raise ImpossibleError('Storage is empty, cannot mount next sample')
        
        self.next_sample = next_sample
        
        
        
        return self.target
     

    def _unmount(self,sm_event):
        """Unmount Sample to Robot arm"""
        
        self.log.info(f"requested sample: {self.value} to be unmounted")
        
        curr_state = self.a_hardware.sm.current_state         
        
        
        if curr_state != SamplechangerSM.home_mounted:
            raise ImpossibleError('Robot is currently not holding sample, cannot unmount sample')
        

        
        if self.a_storage.mag.get_index(self.value) == None:
            raise ImpossibleError('no sample with ID: ' +str(self.value)+' in storage! please, check sample objects stored in storage')
                    
                    
        slot = self.a_storage.mag.get_index(self.value) +1
        
        print(f"slot: {slot}")
        
        # Run Robot script to unmount Sample        
        prog_name = 'messout'+ str(slot) + '.urp'
        
        assert(re.match(r'messout\d+\.urp',prog_name) )
        
        self.a_hardware.run_program(prog_name,sm_event)

        self.status = UNMOUNTING , "Unmounting Sample: " + str(self.value)
        
        self.target = ""

        
        self.read_status()
        
        return self.target

                  
       
    def read_status(self):
            robo_state = self.a_hardware.sm.current_state
            
            if self.a_hardware.status[0] == LOCAL_CONTROL:
                return self.a_hardware.status
        
            
            
            if robo_state in [SamplechangerSM.mounting]:
                return MOUNTING , "Mounting Sample"
            
            if robo_state in [SamplechangerSM.unmounting, SamplechangerSM.unmounting_switch]:
                return UNMOUNTING , "Unmounting Sample"
            
            if robo_state == SamplechangerSM.home_mounted:
                return HOLDING_SAMPLE , "Sample in Special Position"
            
            if robo_state == SamplechangerSM.home:
                return IDLE , "Ready for commands"
            
            return self.a_hardware.status
            

    

        
    @Command()
    def next(self):
        """  (removes (if necessary) old sample and mounts next sample, same as setting 
        the target first to '' and then to 'sampleID')"""

        if self.a_hardware.sm.current_state == SamplechangerSM.home:
            if self.next_sample == '':
                        self.next_sample = self.a_storage.mag.get_next_sample()
                
            self._mount("mount",self.next_sample)
        
        
        if self.a_hardware.sm.current_state == SamplechangerSM.home_mounted:
            self._unmount("mount")
            
            
        
        
        
        
    @Command()
    def stop(self,group = 'control'):
        """Stop execution of program"""
        self.a_hardware.stop()
        return    

    
    
MOUNTING         = Special_Position.Status.MOUNTING
UNMOUNTING       = Special_Position.Status.UNMOUNTING
HOLDING_SAMPLE   = Special_Position.Status.HOLDING_SAMPLE
PAUSED_SAMPLE    = Special_Position.Status.PAUSED
STOPPED_SAMPLE   = Special_Position.Status.STOPPED
LOCAL_CONTROL    = Special_Position.Status.LOCAL_CONTROL 