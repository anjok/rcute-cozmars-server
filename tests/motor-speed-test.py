def motor_adjust_speed(speed, inverse):
   motor_min_value=0.2
   min_value = motor_min_value
   actual_min_value = (min_value if speed>0 else -min_value)
   if inverse:
      return (speed-(actual_min_value))/(1.0 - min_value) if speed else 0
   return speed*(1-min_value) + actual_min_value if speed else 0

for s in range(-10,11):
    speed = s/10
    print(f"in={speed:.3f} out={motor_adjust_speed(speed, False):.3f} inv={motor_adjust_speed(motor_adjust_speed(speed, False), True):.3f}")
