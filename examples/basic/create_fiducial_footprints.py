"""Creates a silkscreen footprints with no pads, from small images. 

White pixels in the image are silkscreened, and black pixels are left blank. 
It's intended that the silkscreen be placed on a dark soldermask.

April tags are downloaded from: https://github.com/AprilRobotics/apriltag-imgs/tree/master/tag36h11.
"""
import cv2
import numpy as np
import requests
from tempfile import NamedTemporaryFile
from dmfwizard.kicad import write_silkscreen_footprint

# List of fiducial codes to create footprints for
OUTPUT_DIR = 'kicad/PurpleDrop.pretty'
FIDUCIAL_IDS = [120, 121, 122]
SIZE = 8 # mm
BORDER = 1 # px

for fid in FIDUCIAL_IDS:
    tag_name = 'tag36_11_%05d' % fid
    footprint_name = f'{tag_name}_%.2fmm' % SIZE
    download_url = f'https://github.com/AprilRobotics/apriltag-imgs/raw/master/tag36h11/{tag_name}.png'
    tempfile = NamedTemporaryFile('wb')
    r = requests.get(download_url)
    r.raise_for_status()
    tempfile.write(r.content)
    tempfile.flush()
    
    image = cv2.imread(tempfile.name)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    w = image.shape[1] + BORDER * 2
    h = image.shape[0] + BORDER * 2
    borderimage = np.ones((h, w)) * 255
    borderimage[BORDER:h-BORDER, BORDER:w-BORDER] = image

    pixel_size = SIZE / w
    write_silkscreen_footprint(borderimage, pixel_size, footprint_name, OUTPUT_DIR, f"Fiducial Tag {fid}")