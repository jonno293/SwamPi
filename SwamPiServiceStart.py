from threading import Thread
import rpyc
import time
import os

def open():
    os.system("python SwamPi.py")

Thread(target=open).start()
time.sleep(3)
conn = rpyc.connect("192.168.1.42", 12345)
conn.root.auto()
