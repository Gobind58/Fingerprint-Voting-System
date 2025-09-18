from pyfingerprint.pyfingerprint import PyFingerprint

class FingerprintSensor:
    def __init__(self):
        self.fp = None

    def connect(self, port, baud=57600):
        self.fp = PyFingerprint(port, baud, 0xFFFFFFFF, 0x00000000)
        if not self.fp.verifyPassword():
            raise RuntimeError("Fingerprint sensor password verify failed")

    def get_template_count(self):
        return self.fp.getTemplateCount()

    def search(self):
        """Return matched template position or None"""
        if self.fp.readImage():
            self.fp.convertImage(0x01)
            result = self.fp.searchTemplate()
            positionNumber = result[0]
            if positionNumber >= 0:
                return positionNumber
        return None

    def enroll(self, positionNumber):
        """Enroll the current finger into given template position."""
        # capture #1
        while not self.fp.readImage():
            pass
        self.fp.convertImage(0x01)

        # ask user to remove finger and place again (handled by GUI prompts)
        # capture #2
        while not self.fp.readImage():
            pass
        self.fp.convertImage(0x02)

        if self.fp.compareCharacteristics() == 0:
            raise RuntimeError("Fingerprints do not match")

        self.fp.createTemplate()
        stored_pos = self.fp.storeTemplate(positionNumber)
        return stored_pos  # normally equals positionNumber

    def delete(self, positionNumber):
        return self.fp.deleteTemplate(positionNumber)

