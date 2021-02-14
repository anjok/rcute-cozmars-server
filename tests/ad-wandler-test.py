import time
import datetime
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
import math
sign = lambda x: math.copysign(1, x)
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c, address=0x48)

chan0 = AnalogIn(ads, ADS.P0)
chan1 = AnalogIn(ads, ADS.P1)
chan2 = AnalogIn(ads, ADS.P2)
(L, R, V) = (0,0,0)
(pL,pR,pV) = (L,R,V)
(roundsL,roundsR) = (0,0)
(prevRoundsL,prevRoundsR) = (roundsL,roundsR)
(rpmL,rpmR) = (0,0)   
print("  {:>8} {:>5}\t|{:>5}t{:>5}t{:>5}\t|{:>5}\t{:>5}\t{:>5}".format("Time","V","L","r","rpm","R","r","rpm"))
items = 5
i = 0
mid = 9
ticksPerSec = 100
roundsCollectInterval = 5 # every 50ms
rpmCollectInterval = 5 # every 5 seconds
rpmCollectsPerMinute = 60 / 5
while True:
    i = i + 1
    (l,r,v) = (chan0.voltage, chan1.voltage, chan2.voltage)
    (L,R,V) = (L+l,R+r,V+v)
    if(i % (rpmCollectInterval*ticksPerSec) == 0):
        (rpmL,rpmR) = ((roundsL-prevRoundsL)*rpmCollectsPerMinute/rpmCollectInterval,(roundsR-prevRoundsR)*rpmCollectsPerMinute/rpmCollectInterval)
        (prevRoundsL,prevRoundsR) = (roundsL,roundsR)
    if(i % roundsCollectInterval == 0):
        if sign(pL-mid) != sign(L-mid):
            roundsL = roundsL+1 
        if sign(pR-mid) != sign(R-mid):
            roundsR = roundsR+1 
        now = datetime.datetime.now().strftime("%H:%M:%S")
        str = "  {:>8} {:>5.3f}\t|{:>5.3f}\t{:>5}\t{:>5.3f}\t|{:>5.3f}\t{:>5}\t{:>5.3f}\t|{:>8.0f}\t{:>8.0f}\t{:>8.0f}".format(now, V/items,L/roundsCollectInterval,roundsL,rpmL,R/roundsCollectInterval,roundsR,rpmR,pL,L,mid)
        print(str, end='\r')
        (pL,pR,pV) = (L,R,V)
        (L,R,V) = (l,r,v)
    if(i % ticksPerSec*60*10 == 0):
        print("")
    time.sleep(1.0/ticksPerSec)
