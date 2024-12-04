# Geolocation accuracy
# Based on your position and pointing knowledge
# This code assumes you have a GPS receiver that creates an error bubble that
# leads to a mispointing even if totally accurate
# Then your pointing accuracy is how well you can point at a target
# We can monte carlo this analysis
# Let's sample a position from the gaussian
import time
start_time = time.time()

import math
import random
import numpy as np

def sin(angle):
    return math.sin(angle*math.pi/180)

def cos(angle):
    return math.cos(angle*math.pi/180)

def asin(value):
    return math.asin(value)*180/math.pi

def main():
    try:
        gps_accuracy = float("{{ digitalforge('gps_accuracy') }}") #mm
        adc_accuracy_pitch = float("{{ digitalforge('adc_accuracy_pitch') }}") # arcseconds
        adc_accuracy_yaw = float("{{ digitalforge('adc_accuracy_yaw') }}") # arcseconds
        #adc_accuracy_roll = 200 # arcseconds
        # https://www.aac-clyde.space/what-we-do/space-products-components/adcs/st200
        distance = float("{{ digitalforge('distance') }}") # km
        min_graze = float("{{ digitalforge('min_graze') }}") # deg
        max_graze = float("{{ digitalforge('max_graze') }}") # deg
    except:
        # Defaults if this didn't work
        gps_accuracy = 1.5 #m
        # https://www.aac-clyde.space/wp-content/uploads/2021/11/GNSS-701.pdf
        adc_accuracy_pitch = 30 # arcseconds
        adc_accuracy_yaw = 30 # arcseconds
        #adc_accuracy_roll = 200 # arcseconds
        # https://www.aac-clyde.space/what-we-do/space-products-components/adcs/st200
        distance = 500 # km
        min_graze = 3 # deg
        max_graze = 90 # deg

    theta_error = random.random()*360 # deg
    phi_error = random.random()*180-90 # deg
    mag_error = random.random()*gps_accuracy # m

    # Position Error
    x = mag_error * cos(theta_error) * sin(phi_error)
    y = mag_error * sin(theta_error) * sin(phi_error)
    z = mag_error * cos(phi_error)

    # Pointing Vector
    act_squint = random.random()*360 # deg
    act_graze = random.random()*(max_graze-min_graze)+min_graze # deg

    # Convert to 2D
    act_elevation = asin(6378.14*sin(90+act_graze)/(distance+6378.14))
    act_range = sin(180-(act_elevation+90+act_graze))/(sin(act_elevation)/6378.14)

    # Add bias
    b_squint = act_squint + ((random.random()*adc_accuracy_pitch)-adc_accuracy_pitch/2)/3600
    b_elevation = act_elevation + ((random.random()*adc_accuracy_yaw)-adc_accuracy_yaw/2)/3600

    #print('Squint Angle: {} deg'.format(act_squint))
    #print('Graze Angle: {} deg'.format(act_graze))
    #print('Elevation Angle: {} deg'.format(90-act_elevation))
    #print('Slant Range: {} km'.format(act_range)) #m
    #print('-'*40)
    #print('Actual Squint: {} deg'.format(b_squint))
    #print('Actual Elevation: {} deg'.format(90-b_elevation))
    #print('-'*40)

    # Create baseline cartesian
    x_t = act_range * cos(act_squint) * sin(180-act_elevation)
    y_t = act_range * sin(act_squint) * sin(180-act_elevation)
    z_t = act_range * cos(180-act_elevation)

    x_1 = 0 + x_t
    y_1 = 6378.14 + distance + z_t
    z_1 = 0 + y_t

    r = x_1**2+y_1**2+z_1**2
    #print('Target Altitude Check: {}'.format(abs(math.sqrt(r)-6378.14)<1e8))

    # Create biased vector
    this_range = distance
    range_iter = 100 # km
    iter_check = False
    while not iter_check:
        #print(this_range)
        x_b = this_range * cos(b_squint) * sin(180-b_elevation)
        y_b = this_range * sin(b_squint) * sin(180-b_elevation)
        z_b = this_range * cos(180-b_elevation)

        x_2 = 0 + x/1000 + x_b
        y_2 = 6378.14 + y/1000 + distance + z_b
        z_2 = 0 + z/1000 + y_b

        r = x_2**2+y_2**2+z_2**2
        #print('Target Altitude Check: {}'.format(abs(math.sqrt(r)-6378.14)<1e-8))

        if abs(math.sqrt(r)-6378.14) < 1e-8:
            iter_check = True
        elif math.sqrt(r)-6378.14 < 0:
            # Went through the earth
            this_range += -range_iter
            range_iter = range_iter / 2
        else:
            if this_range > (6378.14+distance)*2:
                raise NotImplementedError
            this_range += range_iter
    #print('Actual Slant Range: {} km'.format(this_range)) #m
    r = (x_1-x_2)**2+(y_1-y_2)**2+(z_1-z_2)**2
    #print('Geolocation Accuracy: {} km'.format(math.sqrt(r)))
    return math.sqrt(r)

if __name__ == '__main__':
    gla = []
    for i in range(100):
        gla.append(main())

    a = np.array(gla)
    b = []
    for i in range(0,110,10):
        b.append([i, 1000*np.percentile(a, i)])

    print('-'*40)
    print('Maximum: {} m'.format(b[-1][1]))
    np.savetxt("geolocation_output.csv", b, fmt='%.4f', delimiter=",")
    with open("geolocation_output_max.csv", 'w') as f:
        f.write(b[-1][1])

    print("--- %s seconds ---" % (time.time() - start_time))
