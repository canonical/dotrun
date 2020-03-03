# Standard library
import os
from hashlib import md5


def file_md5(filename):
    """
    Produce an MD5 hash value from the contents of a file
    """

    file_hash = None

    if os.path.isfile(filename):
        file_hash = md5()

        with open(filename, "rb") as file_handler:
            for chunk in iter(lambda: file_handler.read(4096), b""):
                file_hash.update(chunk)

    return file_hash.hexdigest()
