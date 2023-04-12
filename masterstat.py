import pigpio
import RPi.GPIO as GPIO

pi = pigpio.pi()

pi.wave_tx_stop()

pin = 23

GPIO.setmode(GPIO.BCM)
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