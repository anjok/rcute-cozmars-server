from gpiozero import LineSensor
from signal import pause
import time

pull_up=True
left = LineSensor(16,queue_len=3, sample_rate=10, pull_up=pull_up)
left.when_line = lambda: print('Left detected')
left.when_no_line = lambda: print('Left not detected')
right = LineSensor(12,queue_len=3, sample_rate=10, pull_up=pull_up)
right.when_line = lambda: print('Right detected')
right.when_no_line = lambda: print('Right not detected')
while True:
  print("{},{}".format(left.value, right.value))
  time.sleep(1)

