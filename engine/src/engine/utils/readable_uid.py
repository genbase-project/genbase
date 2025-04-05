from hrid import HRID




def generate_readable_uid():
    hruuid = HRID()
    uuid = hruuid.generate()
    return uuid