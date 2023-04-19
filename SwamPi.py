import time
import rpyc
import sqlite3
import logging
from threading import Thread

####Settings
boardType = 1 #1 = Raspberrypi; 2 = Le Potato
CtrlMethod = 1 #1: masterstat; 2: Relay Board; NOTE: Not yet able to run masterstat with Le Potato
PreWet = 75 #time in seconds to prewet pads before starting pump
postWet = 75
loopTime = 20 #time in seconds to wait before rechecking for thermostat control

purgePumpEnable = 1 #1 or 0 if using purge pump
purgePumpFreq = 6 #amount of runtime in hours that elapses between purge pump runs
purgePumpRunTime = 4 #amount of time in minutes purge pump runs during cycle

####Initialize system parameters, Don't Change
serverMode = 0; # 0 = off; 1 = auto; 2 = override controls that auto and manual cannot run at the same time
switch = [0,0,0,0]
running = 0
runTime = 0
startTime = 0
purging = 0

if boardType == 1:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
elif boardType == 2:
    import LePotatoPi.GPIO.GPIO as GPIO

pinCoolHi = 17
pinCoolLo = 27
pinFan = 4
GPIO.setup(pinCoolHi,GPIO.IN,GPIO.PUD_DOWN)
GPIO.setup(pinCoolLo,GPIO.IN,GPIO.PUD_DOWN)
GPIO.setup(pinFan,GPIO.IN,GPIO.PUD_DOWN)

if CtrlMethod == 1:
    import os
    os.system("sudo pigpiod")
    import pigpio
    pi = pigpio.pi()
    pi.wave_tx_stop()
    pin = 23
    GPIO.setwarnings(False)
    GPIO.setup(pin,GPIO.OUT)
    def control(switches):
        totalOn = sum(switches)
        remainingTime = 885600-totalOn*5600
        pulse = []
        pulse.append(pigpio.pulse(1<<pin,0,31200))
        pulse.append(pigpio.pulse(0,1<<pin,2000))
        pulse.append(pigpio.pulse(1<<pin,0,11200))
        pulse.append(pigpio.pulse(0,1<<pin,2000))
        pulse.append(pigpio.pulse(1<<pin,0,11200))
        pulse.append(pigpio.pulse(0,1<<pin,2000))
        pulse.append(pigpio.pulse(1<<pin,0,11200))
        pulse.append(pigpio.pulse(0,1<<pin,2000))
        pulse.append(pigpio.pulse(1<<pin,0,11200))
        pulse.append(pigpio.pulse(0,1<<pin,2000))
        pulse.append(pigpio.pulse(1<<pin,0,5600+5600*switches[0]))
        pulse.append(pigpio.pulse(0,1<<pin,2000))
        pulse.append(pigpio.pulse(1<<pin,0,5600+5600*switches[1]))
        pulse.append(pigpio.pulse(0,1<<pin,2000))
        pulse.append(pigpio.pulse(1<<pin,0,5600+5600*switches[2]))
        pulse.append(pigpio.pulse(0,1<<pin,2000))
        pulse.append(pigpio.pulse(1<<pin,0,5600+5600*switches[3]))
        pulse.append(pigpio.pulse(0,1<<pin,remainingTime))

        
        pi.wave_clear()
        pi.wave_add_new()

        pi.wave_add_generic(pulse)

        wave = pi.wave_create()

        pi.wave_send_repeat(wave)
        
    def stop():
        pi.wave_tx_stop()

elif CtrlMethod == 2:
    GPIO.setup(12,GPIO.OUT) #FanHi
    GPIO.setup(16,GPIO.OUT) #FanLo
    GPIO.setup(21,GPIO.OUT) #PurgePump
    GPIO.setup(20,GPIO.OUT) #Pump
    def control(switches):
        GPIO.output(12, switches[0])
        GPIO.output(16, switches[1])
        GPIO.output(21, switches[2]) #PurgePump
        GPIO.output(20, switches[3])
   
#print("setup Complete")
   
class ServerService(rpyc.Service):
    def exposed_manual(self,fanHi,fanLo,purgePump,pump):
        global serverMode
        global running
        serverMode = 2
        toggle = [fanHi,fanLo,purgePump,pump].index(1)
        if switch[toggle] == 1:
            switch[toggle] = 0
        else:
            switch[toggle] = 1
        sendCmd()
        if switch[3]:
            if switch[0]:
                running = 2
            elif switch[1]:
                running = 1
        else: running = 0
        logging.info(["Manual Override, switch = ", switch])
    def exposed_auto(self):
        global serverMode
        serverMode = 1
        global running #0 = off; 1 = coolLo; 2 = coolHi
        global switch
        return 0
        while serverMode == 1:
            nestcmd = [GPIO.input(pinCoolHi),GPIO.input(pinCoolLo),GPIO.input(pinFan)]
            #print("reading", nestcmd, running)
            logging.debug(["reading ; nest cmd = ", nestcmd,"running = ", running])
            if running == 0:
                if nestcmd[1] == 1 or nestcmd[0] == 1:
                    switch = ([0,0,0,1])
                    sendCmd()
                    time.sleep(PreWet)
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
                    #print("shutting down")
                    switch = ([0,0,0,1])
                    sendCmd()
                    #print("and again")
                    time.sleep(postWet)
                    switch = ([0,0,0,0])
                    sendCmd()
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
            time.sleep(loopTime)
    def exposed_getSwitch(self):
        global switch
        return switch
    
def sendCmd():
    global switch
    global running
    global startTime
    global runTime
    global purging
    if switch[0] == 1 and switch[1] == 1: #Disable running Low and High at the same time
        switch[1] = 0
    if switch[0] or switch[1]:
        if running == 0:
            startTime = time.time()
        else:
            runTime = runTime + time.time() - startTime
    else:
        if running != 0:
            runTime = runTime + time.time() - startTime
    if purging == 1: switch[2] = 1 #in case sendCmd() is called during purging
    #print("running control ",switch,running)
    logging.info(["Sending Command, switch = ",switch])
    control(switch)
    
def runPurge():
    global purgePumpFreq
    global purgePumpRunTime
    global runTime
    global purging
    while True:
        if runTime > purgePumpFreq*3600:
            global switch
            logging.info("Starting Purge Cycle")
            purging = 1
            switch[2] = 1
            sendCmd()
            time.sleep(purgePumpRunTime*60)
            switch[2] = 0
            purging = 0
            sendCmd()
            runTime = 0
        time.sleep(60*10)
    
logging.basicConfig(filename='/home/pi/SwamPi/log.log',
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%m-%d-%y %H:%M:%S',
                    level=logging.INFO)                       
 
if purgePumpEnable == 1: Thread(target=runPurge).start()
 
from rpyc.utils.server import ThreadedServer
t = ThreadedServer(ServerService, port = 12345)
logging.info("Setup Complete, starting Server")
t.start()
