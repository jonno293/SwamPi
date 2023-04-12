import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(12,GPIO.OUT) #FanHi
GPIO.setup(16,GPIO.OUT) #FanLo
GPIO.setup(21,GPIO.OUT) #PurgePump
GPIO.setup(20,GPIO.OUT) #Pump

def control(switches):
    GPIO.output(12, switches[0])
    GPIO.output(16, switches[1])
    GPIO.output(21, switches[2]) #PurgePump
    GPIO.output(20, switches[3])
