class AudioService:
    def __init__(self, speaker=None):
        self.speaker = speaker

    def speak(self, text: str, interrupt: bool = False):
        if self.speaker:
            try:
                self.speaker.speak(text, interrupt=interrupt)
            except Exception:
                pass

    def play_sound(self, sound_id: str):
        # Placeholder hook for future sound effects/music support.
        return None
