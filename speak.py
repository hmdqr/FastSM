"""Speech output using accessible_output2."""

from accessible_output2 import outputs

speaker = outputs.auto.Auto()

def speak(text, interrupt=False):
	speaker.speak(text, interrupt)
