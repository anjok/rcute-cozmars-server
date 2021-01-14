from gpiozero import Button
button = Button(4,pull_up=False)
button.wait_for_press()
