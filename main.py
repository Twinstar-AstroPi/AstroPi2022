from pathlib import Path
from logzero import logger, logfile
from sense_hat import SenseHat
from picamera import PiCamera
from orbit import ISS
from time import sleep
from datetime import datetime, timedelta
import csv

#
#  Mission Spacelab Team 'Twin Stars'
#  In-orbit Earth magnetic field sampling to analyse
#  anomalies at particular geological formations
#

def create_csv_file(data_file):
    """Create a new CSV file and add the header row"""
    with open(data_file, 'w') as f:
        writer = csv.writer(f)
        header = ("Counter", "Date/time", "Latitude", "Longitude", "Temperature", "Humidity", "MagX", "MagY", "MagZ","Pitch","Roll","Yaw","X_Acc","Y_Acc","Z_Acc")
        writer.writerow(header)

def add_csv_data(data_file, data):
    """Add a row of data to the data_file CSV"""
    with open(data_file, 'a') as f:
        writer = csv.writer(f)
        writer.writerow(data)

def convert(angle):
    """
    Convert a `skyfield` Angle to an EXIF-appropriate
    representation (rationals)
    e.g. 98° 34' 58.7 to "98/1,34/1,587/10"

    Return a tuple containing a boolean and the converted angle,
    with the boolean indicating if the angle is negative.
    """
    sign, degrees, minutes, seconds = angle.signed_dms()
    exif_angle = f'{degrees:.0f}/1,{minutes:.0f}/1,{seconds*10:.0f}/10'
    return sign < 0, exif_angle

def capture(camera, image):
    """Use `camera` to capture an `image` file with lat/long EXIF data."""
    location = ISS.coordinates()

    # Convert the latitude and longitude to EXIF-appropriate representations
    south, exif_latitude = convert(location.latitude)
    west, exif_longitude = convert(location.longitude)

    # Set the EXIF tags specifying the current location
    camera.exif_tags['GPS.GPSLatitude'] = exif_latitude
    camera.exif_tags['GPS.GPSLatitudeRef'] = "S" if south else "N"
    camera.exif_tags['GPS.GPSLongitude'] = exif_longitude
    camera.exif_tags['GPS.GPSLongitudeRef'] = "W" if west else "E"

    # Capture the image
    camera.capture(image)

# Set base folder for data, logs and photos
base_folder = Path(__file__).parent.resolve()

# Set a logfile name
logfile(base_folder/"events.log")

# Set duration
minutes_to_run = 175 

# Set seconds between sampling
sampling_delta_secs = 10

# Total photo size and maximum allowed
photos_size = 0
max_photos_size = 2684354560 # Don't exceed 2,5 Gb

# Set up Sense Hat
sense = SenseHat()
sense.rotation = 90
sense.clear()

# Set up camera
cam = PiCamera()
cam.resolution = (1296, 972)

# Initialise the CSV file
data_file = base_folder/"data.csv"
create_csv_file(data_file)

# Initialise the photo counter
counter = 1

# Record the start and current time
start_time = datetime.now()
now_time = datetime.now()
# Run a loop for (almost) three hours

while (now_time < start_time + timedelta(minutes= minutes_to_run)):
    try:

        # Sample magnetic vectors
        mag = sense.get_compass_raw()
        mag_x = round(mag["x"],2)
        mag_y = round(mag["y"],2)
        mag_z = round(mag["z"],2)
        
        # Get orientation 
        o = sense.get_orientation()
        pitch = round(o["pitch"], 3)
        roll = round(o["roll"], 3)
        yaw = round(o["yaw"], 3)
        
        # Acceleration
        acceleration = sense.get_accelerometer_raw()
        x_acc = round(acceleration['x'], 3)
        y_acc = round(acceleration['y'], 3)
        z_acc = round(acceleration['z'], 3)
        
        # Sample local temp and humidity, we want to share
        # data with the other team project for life in space
        humidity = round(sense.humidity, 2)
        temperature = round(sense.temperature, 2)
      
        # Get coordinates of location on Earth below the ISS
        location = ISS.coordinates()
        # Save the data to the file
        data = (
            counter,
            datetime.now(),
            location.latitude.degrees,
            location.longitude.degrees,
            temperature,
            humidity,
            mag_x,
            mag_y,
            mag_z,
            pitch,
            roll,
            yaw,
            x_acc,
            y_acc,
            z_acc
        )
        add_csv_data(data_file, data)
        
        # Capture image if there is enough space
        if photos_size < max_photos_size :
            image_file = f"{base_folder}/photo_{counter:04d}.jpg"
            capture(cam, image_file)
            # Update total photo size
            photos_size += Path(image_file).stat().st_size
            # Log event
            logger.info(f"iteration {counter} photo size {photos_size}")
        else:
            logger.info(f"iteration {counter} Max photos size reached.")
        # Update counter
        counter += 1
        # pause - sampling delta
        sleep(sampling_delta_secs)
        # Update the current time
        now_time = datetime.now()
    except Exception as e:
        logger.error(f'{e.__class__.__name__}: {e}')
        
logger.info(f"Ended on iteration {counter}.")        