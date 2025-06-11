import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__name__)))
nsamples = 12

Node('sample_changer.HZB',  # a globally unique identification # type: ignore
     'Sample Changer\n\nThis is an demo for a  SECoP (Sample Environment Communication Protocol) sample changer SEC-Node.',  # describes the node
      'tcp://2205',
      implementor = 'Peter Wegmann')  # you might choose any port number > 1024

Mod('robot_io',  # the name of the module # type: ignore
    'frappy_HZB.hardware.RobotIO',  # the class used for communication
    'TCP communication to robot Dashboard Server Interface',  # a description
    uri='tcp://192.168.3.5:29999', 
    #uri='tcp://localhost:29999', 
)    
    
Mod('hardware', # type: ignore
    'frappy_HZB.hardware.hardware',
    'The hardware component responsible for physically moving the samples',
    io='robot_io',

    
    model = "none",
    serial = "none",
    ur_version = "none",
    
   
    pollinterval = 0.1,

)


Mod('storage', # type: ignore
    'frappy_HZB.storage.Storage',
    'Hardware component that holds a number of samples in sample slots',
    a_sample = 'sample_at_measurement_position',
    a_hardware = 'hardware',
    pollinterval = 1
  
)


Mod('sample_at_measurement_position', # type: ignore
    'frappy_HZB.special_position.Special_Position',
    'Sample currently present at the measuerement position',
    a_hardware = 'hardware',
    a_storage = 'storage',
    pollinterval = 1,

    )
