import pyttsx3

engine = pyttsx3.init()

voices = engine.getProperty("voices")
engine.setProperty("voice", voices[2].id) 
engine.setProperty("rate", 170)
engine.setProperty("volume", 1.0)
engine.say("Emergency ! Oncoming vehicle entering your lane. !")
engine.save_to_file("Emergency ! Oncoming vehicle entering your lane. !", "assets/audio/scenario6.wav")
engine.runAndWait()