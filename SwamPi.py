import RPi.GPIO as GPIO
import time
import rpyc
import sqlite3

GPIO.setmode(GPIO.BCM)

pinCoolHi = 17
pinCoolLo = 27
pinFan = 4

GPIO.setup(pinCoolHi,GPIO.IN,GPIO.PUD_DOWN)
GPIO.setup(pinCoolLo,GPIO.IN,GPIO.PUD_DOWN)
GPIO.setup(pinFan,GPIO.IN,GPIO.PUD_DOWN)

####Settings
CtrlMethod = 2 #1: masterstat; 2: Relay Board
PreWet = 75 #time in seconds to prewet pads before starting pump

####Initialize system parameters
serverMode = 0; # 0 = off; 1 = auto; 2 = override controls that auto and manual cannot run at the same time
switch = [0,0,0,0]
running = 0
runTime = 0

if CtrlMethod == 1:
    import os
    os.system("sudo pigpiod")
    import masterstat as ctrl #input is [fanhi,fanLo,PurgePump,Pump]
if CtrlMethod == 2:
    import RelayBoard as ctrl
    
class ServerService(rpyc.Service):
    def exposed_manual(self,fanHi,fanLo,purgePump,pump):
        global serverMode
        serverMode = 2
        toggle = [fanHi,fanLo,purgePump,pump].index(1)
        if switch[toggle] == 1:
            switch[toggle] = 0
        else:
            switch[toggle] = 1
        sendCmd()
        
        print(switch)
    def exposed_auto(self):
        global serverMode
        serverMode = 1
        global running #0 = off; 1 = coolLo; 2 = coolHi
        global runTime
        global switch
        while ServerMode == 1:
            nestcmd = [GPIO.input(pinCoolHi),GPIO.input(pinCoolLo),GPIO.input(pinFan)]
            if running == 0:
                if nestcmd[1] == 1 or nestcmd[0] == 1:
                    switch = ([0,0,0,1])
                    sendCmd()
                    time.sleep(PreWet)
                    #startTime = time.time()
                    if nestcmd[0] == 1: #High
                        switch = ([1,0,0,1])
                        sendCmd()
                        running = 2
                    elif nestcmd[1] == 1: #Low
                        switch = ([0,1,0,1])
                        sendCmd()
                        running = 1
            elif running != 0:
                if nestcmd[1] == 0 and nestcmd[0] == 0: #was running last loop but not anymore
                    #runTime = runTime + time.time() - startTime
                    switch = ([0,0,0,1])
                    sendCmd()
                    time.sleep(PreWet)
                    switch = ([0,0,0,0])
                    sendCmd()
                    startTime = 0
                    running = 0
                if (nestcmd[1] == 1 or nestcmd[0] == 1):
                    if nestcmd[0] == 1 and running == 1: #Changing to High
                        switch = ([1,0,0,1])
                        sendCmd()
                        running = 2
                    elif nestcmd[1] == 1 and running == 2: #Changing to Low
                        switch = ([0,1,0,1])
                        sendCmd()
                        running = 1
            time.sleep(30)
    def exposed_getSwitch(self):
        return switch
    
def sendCmd():
    global switch
    if switch[0] == 1 and switch[1] == 1: #Disable running Low and High at the same time
        switch[1] = 0
    if switch[0] or switch[1]:
        if running == 0:
            startTime = time.time()
    else:
        if running != 0:
            runTime = runTime + time.time() - startTime
    ctrl.control(switch)
    
 
from rpyc.utils.server import ThreadedServer
t = ThreadedServer(ServerService, port = 12345)
t.start()