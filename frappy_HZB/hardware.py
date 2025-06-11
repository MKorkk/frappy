import re

from frappy.core import BUSY, ERROR, IDLE, Command, HasIO, Parameter, \
    Readable, StatusType, StringIO, StructOf
from frappy.datatypes import ArrayOf, BoolType, EnumType, FloatRange, \
    StringType
from frappy.errors import ImpossibleError, InternalError, IsBusyError, \
    IsErrorError, ReadFailedError
from frappy.lib.enum import Enum
from frappy.modules import Attached

from samplechanger_sm import SamplechangerSM
from robot_server import RobotServer
from frappy.lib import clamp, mkthread


import time

ROBOT_MODE_ENUM = {
    'NO_CONTROLLER'  :0,
    'DISCONNECTED'   :1,
    'CONFIRM_SAFETY' :2,
    'BOOTING'        :3,
    'POWER_OFF'      :4,
    'POWER_ON'       :5,
    'IDLE'           :6,
    'BACKDRIVE'      :7,
    'RUNNING'        :8          
}

SAFETYSTATUS = {
    'NORMAL' :0,
    'REDUCED' :1,
    'PROTECTIVE_STOP' :2,
    'RECOVERY' :3,
    'SAFEGUARD_STOP' :4,
    'SYSTEM_EMERGENCY_STOP' :5,
    'ROBOT_EMERGENCY_STOP' :6,
    'VIOLATION' :7,
    'FAULT' :8,
    'AUTOMATIC_MODE_SAFEGUARD_STOP' :9,
    'SYSTEM_THREE_POSITION_ENABLING_STOP' :10,
    'UNKNOWN':11

} 




class RobotIO(StringIO):
    
    default_settings = {'port': 29999}
    wait_before = 0.05
    
    

        


class hardware(HasIO,Readable):    
    
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.sm = SamplechangerSM()
        self.callbacks = [
            ('ok','run_program',self.run_program_ok_callback),
            ('error', 'run_program',self.run_program_error_callback)
        ]
        self.robo_server = RobotServer(self.sm,self.callbacks,logger=self.log)
        self.sm.set_wait_idle_callback(self.wait_idle_cb)  


    
    ioClass = RobotIO
    
    Status = Enum( 
        Readable.Status,
        DISABLED = StatusType.DISABLED,
        STANDBY = StatusType.STANDBY,
        BUSY     = StatusType.BUSY,
        PAUSED = 305,
        PREPARING = StatusType.PREPARING,
        STOPPED = 402,
        LOCAL_CONTROL = 403,
        LOCKED = 404,        
        UNKNOWN = StatusType.UNKNOWN                
        )  #: status codes
    
    def initModule(self):
        super().initModule()
        self._thread = mkthread(self.robo_server.start_server_in_thread)

    status = Parameter(datatype=StatusType(Status))  # override Readable.status

    
    
    value = Parameter("Currently loaded program",
                       datatype=StringType(),
                       default = '<unknown>.urp',
                       readonly = True)
    
    loaded_prog = Parameter("Program that is currently loaded",
                            datatype= StringType(),
                            default = "<unknown>.urp",
                            readonly = True,
                            visibility = 'expert')
    
    model = Parameter("Model name of the robot",
                      datatype=StringType(),
                      default = "none",                
                      readonly = True,
                      group = "Robot Info")
    
    serial = Parameter("Serial number of connected robot",
                       datatype=StringType(),
                       default = "none",
                       readonly = True,
                       group = "Robot Info")
    
    ur_version = Parameter("Version number of the UR software installed on the robot",
                           datatype=StringType(),
                           default = "none",
                           readonly = True,
                           group = "Robot Info",
                           visibility = 'expert')
    
    robotmode = Parameter("Current mode of robot",
                          datatype=EnumType("Robot Mode",ROBOT_MODE_ENUM),
                          default = "DISCONNECTED",
                          readonly = True,
                          group = "Status Info")
    
    powerstate = Parameter("Powerstate of robot",
                           datatype=EnumType("Pstate",POWER_OFF= None,POWER_ON = None ),
                           default = "POWER_OFF" ,
                           readonly = False,
                           group = "Status Info")
    
    safetystatus = Parameter("Safetystatus: Specifying if a given Safeguard Stop was caused by the permanent safeguard I/O stop,a configurable I/O automatic mode safeguard stop or a configurable I/O three position enabling device stop.",
                             datatype=EnumType(SAFETYSTATUS),
                             default = "NORMAL",
                             readonly = True,
                             group = 'Status Info')

    
    program_running = Parameter("Program running status",
                                datatype=BoolType,
                                default = False,
                                readonly = True,
                                group = 'Status Info')
    
    was_running = Parameter("Last Program running status",
                                datatype=BoolType,
                                default = False,
                                readonly = True,
                                export = False
                                )

    

    
    is_in_remote_control = Parameter("Control status of robot arm",
                                     datatype=BoolType,
                                     readonly = True,
                                     default = False,
                                     group = 'Status Info')
       
    def wait_idle_cb(self):

        timeout = time.time() + 5   # 5 Second Timeout
        while self._program_running():
            if time.time() > timeout:
                raise Exception("timeout")
            time.sleep(0.2)
            
                    
        self.read_status()
            
        

       
    
    def doPoll(self):
        self.read_value()
        self.read_status()


    def reconnect_communicator(self):
        """reconnects to Robot"""
        self.io.closeConnection()
        
        self.io.connectStart()
  


    def read_is_in_remote_control(self):
        remote_control =  str(self.communicate('is in remote control'))
        
        if remote_control == 'true':
            if not self.is_in_remote_control:
                self.reconnect_communicator()
        
            self.is_in_remote_control = True
            return True
        
        
        
        self.is_in_remote_control = False
        return False

    def read_safetystatus(self):
        safety_stat = str(self.communicate('safetystatus')).removeprefix("Safetystatus: ")

        if safety_stat in SAFETYSTATUS:
            return safety_stat

        raise ReadFailedError("Unknown safetytatus:" + safety_stat)

   
    
    
    def _run_loaded_program(self):
        play_reply  = str(self.communicate('play'))
        

        
        if play_reply == 'Starting program':
            self.status = BUSY, "Starting program"
        else:
            raise InternalError("Failed to execute: play")
        
    
    def read_loaded_prog(self):
        loaded_prog_reply =  str(self.communicate('get loaded program'))

        if loaded_prog_reply == 'No program loaded':
            return 'no_program_loaded'
        else:
            return re.search(r'([^\/]+.urp)',loaded_prog_reply).group()

        
    
    def read_value(self):
        return self.read_loaded_prog()



    def read_model(self):
        return str(self.communicate('get robot model'))

    def read_serial(self):
        return str(self.communicate('get serial number'))
    

    def read_ur_version(self):
        return str(self.communicate('version'))
    
    def read_robotmode(self):
        robo_mode =  str(self.communicate('robotmode')).removeprefix('Robotmode: ')
    
        if robo_mode in ROBOT_MODE_ENUM:
            return robo_mode

        raise ReadFailedError("Unknown robot mode:" + robo_mode)
    
    def read_powerstate(self):
        self.read_robotmode()
        if self.robotmode.value > 4:
            return 'POWER_ON' 
        else:
            return 'POWER_OFF'
    
    
    def write_powerstate(self,powerstate):
        p_str = powerstate.name
        
        self.communicate(POWER_STATE.get(p_str,None))
        
        if powerstate == 'POWER_ON':
            self.communicate('brake release')
        
        
        self.powerstate = self.read_powerstate()
        
        return powerstate.name

    
    def read_status(self):
    
        if not self.read_is_in_remote_control():
            return LOCAL_CONTROL, "Robot is in 'local control' mode"

        self.read_safetystatus()
        if  self.safetystatus > 1:
            return LOCKED, str(self.safetystatus.name)
        
        
               
       
        if self.status[0] == STOPPED:
            return self.status
                
        if self.status[0] == ERROR:
            return self.status
        
        if self.status[0] == UNKNOWN:
            return self.status
        
        if self._program_running():
            return BUSY, f'Robot is running program. Robot State: {self.sm.current_state.name}'
        
        
        if self.sm.current_state == SamplechangerSM.home or self.sm.current_state == SamplechangerSM.home_mounted:
            return IDLE, 'Robot is at home position'
        else:
            return BUSY, f'Robot is running program. Robot State: {self.sm.current_state.name}'

        
        



    def read_program_running(self):
        running = self._program_running()
        
        if self.was_running and  (running == False):
            self.read_status()
            
        
        self.was_running = running
        
        
        
        
        return running 

    def _program_running(self): 
        running_reply = str(self.communicate('running')).removeprefix('Program running: ') 
        
        if running_reply == 'true':
            return True
        
        return False
    
   


    @Command(group ='control')
    def stop(self):
        """Stop execution of program"""
        
        # already stopped
        if self.status[0] == STOPPED:
            raise ImpossibleError('module is already stopped')

        if self._program_running():     
            stop_reply  = str(self.communicate('stop'))
        
            if stop_reply ==  'Stopped':
                self.status = STOPPED, "Stopped execution"
                
            
            elif stop_reply == 'Failed to execute: stop':
                raise InternalError("Failed to execute: stop")
            
    def run_program(self,program_name,sm_event):
        if self.safetystatus > SAFETYSTATUS['REDUCED']:
            raise IsErrorError('Robots is locked due to a safety related problem (' + str(self.safetystatus.name) + ") Please refer to instructions on the controller tablet or try 'clear_error' command.")
            
        
        if not self.read_is_in_remote_control():
            raise ImpossibleError('Robot arm is in local control mode, please switch to remote control mode on the Robot controller tablet')
        
        if self.status[0] == BUSY or self.status[0] == PREPARING:
            if not self._program_running() and self.sm.current_state == SamplechangerSM.home_switch:
                pass
            else:
                raise IsBusyError('Robot is already executing another program')
        
        if self.status[0] >= 400 and self.status[0] != STOPPED:
            raise IsErrorError("Robot is in an error state. program '"+program_name+ "' cannot be exectuted")
        
        load_reply = str(self.communicate(f'load {program_name}'))
              
        
        if re.match(r'Loading program: .*%s' % program_name,load_reply):
            self._run_loaded_program()
            self.value = program_name
            
           
        elif re.match(r'File not found: .*%s' % program_name,load_reply):
            raise InternalError('Program not found: '+program_name)
        
        elif re.match(r'Error while loading program: .*%s' % program_name,load_reply):
            raise InternalError('write_target ERROR while loading program: '+ program_name)
            
        else:
            self.status = ERROR, 'unknown answer: '+ load_reply 
            raise InternalError('unknown answer: '+load_reply)
        
        self.sm.send(sm_event)
    

    def error_occurred(self,error_message):
        if error_message:
            self.status = ERROR, f'Reason:{error_message}'
        else:
            self.status = ERROR, 'An unknown error occurred' 
        
        self.read_status()
   
    def run_program_ok_callback(self):
        # Robot successfully unmounted the sample
        pass
    
    def run_program_error_callback(self,message):
        # Error while running program
        self.status = ERROR, message
        self.read_status()
   
   
    @Command(StringType(maxchars=40),group = 'control')
    def run_program_by_path(self,program_name):
        """Runs the requested program on the robot"""
        self.run_program(program_name,'run_program')

        
    
  


            
            
    
  
PAUSED           = hardware.Status.PAUSED
STOPPED          = hardware.Status.STOPPED
UNKNOWN          = hardware.Status.UNKNOWN
PREPARING        = hardware.Status.PREPARING
DISABLED         = hardware.Status.DISABLED
STANDBY          = hardware.Status.STANDBY 
LOCAL_CONTROL    = hardware.Status.LOCAL_CONTROL 
LOCKED           = hardware.Status.LOCKED
ERROR            = hardware.Status.ERROR

ROBOT_MODE_STATUS = {
    'NO_CONTROLLER' :(ERROR,'NO_CONTROLLER'),
    'DISCONNECTED' :(DISABLED,'DISCONNECTED'),
    'CONFIRM_SAFETY' :(DISABLED,'CONFIRM_SAFETY'),
    'BOOTING' :(PREPARING,'BOOTING'),
    'POWER_OFF' :(DISABLED,'POWER_OFF'),
    'POWER_ON' :(STANDBY,'POWER_ON'),
    'IDLE' :(IDLE,'IDLE'),
    'BACKDRIVE' :(PREPARING,'BACKDRIVE'),
    'RUNNING' :(IDLE,'IDLE'),
}



POWER_STATE = {
    'POWER_ON'  : 'power on',
    'POWER_OFF' : 'power off'
}


