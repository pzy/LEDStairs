#!/usr/bin/env python3
# rpi_ws281x library strandtest example
# Author: Tony DiCola (tony@tonydicola.com)
#
# Direct port of the Arduino NeoPixel library strandtest example.  Showcases
# various animations on a strip of NeoPixels.

import time
import argparse
import math
import random
import sys
import logging
from random import seed
import RPi.GPIO as GPIO
from threading import Thread, Lock
from rpi_ws281x import *
from neopixel import Adafruit_NeoPixel,Color

# LED strip configuration:
LED_PIN        = 18      # GPIO pin connected to the pixels (18 uses PWM!).
LIGHT_PIN      = 2       # GPIO pin light sensor is connected to since we do not use an analog to digital converter we can only get lights on or lights off
LIGHT_BRIGHTNESS=170     # brightness on strip when light is detected
DARK_BRIGHTNESS=40       # brightness on strip when lights are off
MOTION_PIN     = 17      # pin the first motion sensor connected to (depending on which sensor is hit the strips starts the aniimation form top or from bottom)
MOTION2_PIN     = 27     # pin the second motion sensor is connected to
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = DARK_BRIGHTNESS # Set to 0 for darkest and 255 for brightest, default brightness, will be overwritten by light or dark brightness
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
#CUSTOM_STEP_LENGTH=[60, 64, 84, 65, 58 , 58, 58, 58, 58, 58, 58, 58, 58, 58, 55, 55, 55];
CUSTOM_STEP_LENGTH=[63, 51, 50, 56, 56 , 56, 56, 57, 57, 56, 56, 56, 57, 62, 82, 62, 58 ];
#CUSTOM_STEP_LENGTH=[2, 4, 3, 5 , 1, 15]
CUSTOM_STEP_STARTS=[]
ANIMATION_MILLIES=0.005
ON=False
ANIMATION_RUN=False
ANIMATION_THREAD=None
TIMEOUT_THREAD=None
TIMEOUT_RUN=False
TIMEOUT_TIME=50
DARK=True
COLOR=Color(0,0,255)
WORKING=Lock()
fdelay=0.001
idelay=0.001
EFFECT="Rainbow"

def rainbowColor(pos):
    colors= [ Color(0, 255, 0), Color(127, 255, 0), Color(255, 255, 0), Color(255, 0, 0), Color(0,0,255), Color(43,46,95), Color(0, 139,255) ]
    pos=pos-1
    return colors[pos%len(colors)]

def setColor(strip, color, step=None, reverse=False, rangeColor=0, show=True, showPixel=True, pdelay=0):
    if step==None:
        if reverse:
            for i in range(len(CUSTOM_STEP_LENGTH),0,-1):
                setStep(strip, i, color, show, showPixel, ANIMATION_MILLIES, reverse, rangeColor);
                time.sleep(0.5)
        else:
            for i in range(1, len(CUSTOM_STEP_LENGTH)+1):
                setStep(strip, i, color, show, showPixel, ANIMATION_MILLIES, reverse, rangeColor);
                time.sleep(0.5)
                #setStep(strip, i, color, True, True, ANIMATION_MILLIES, reverse);
    else:
        setStep(strip, step, color, show, showPixel, ANIMATION_MILLIES, reverse, rangeColor);
        time.sleep(0.5)
        #setStep(strip, step, color, True, True, ANIMATION_MILLIES, reverse, rangeColor);

def setStep(strip, stepNo, color, show=False, showPixel=False, delay=1.0, reverse=False, rangeColor=0):
    start=0
    stop=0
    step=1
    o_r=((color >> 16) & 0xFF)
    o_g=((color >> 8) & 0xFF)
    o_b=(color & 0xFF)
    r=o_r
    g=o_g
    b=o_b
    rr=0
    rg=0
    rb=0
    if rangeColor>0:
        rr=(rangeColor >> 16) & 0xFF
        if rr>o_r:
            rr=o_r/2
        rg=(rangeColor >> 8) & 0xFF
        if rg>o_g:
            rg=o_g/2
        rb=(rangeColor) & 0xFF
        if rb>o_b:
            rb=o_b/2
    if reverse:
        start=CUSTOM_STEP_STARTS[stepNo-1]+CUSTOM_STEP_LENGTH[stepNo-1]-1
        stop=CUSTOM_STEP_STARTS[stepNo-1]-1
        step=-1
    else:
        start=CUSTOM_STEP_STARTS[stepNo-1]
        stop=start+CUSTOM_STEP_LENGTH[stepNo-1]
    #logging.info("Setting step:" + str(stepNo) + " LED: " + str(start) + " - " + str(stop))
    for i in range(start,stop, step):
        if rangeColor>0:
            #logging.info str(rr) +","+str(rg)+","+str(rb)
            if rr>0:
                r=random.randrange(o_r-rr, o_r+rr)
            if rg>0:
                g=random.randrange(o_g-rg, o_g+rg)
            if rb>0:
                b=random.randrange(o_b-rb, o_b+rb)
        strip.setPixelColor(i, Color(r,g,b, 255))
        #if showPixel:
        #    strip.show()
            #time.sleep(delay/10)
    if show:
        strip.show()


def iceSteps(strip, reverse=False):
    global idelay
    if not reverse:
        for i in range(1, len(CUSTOM_STEP_LENGTH)+1):
            setColor(strip, Color(0, 0, 200), i, reverse, Color(0,0,40), True, False, idelay) 
    else:
        for i in range(len(CUSTOM_STEP_LENGTH),0,-1):
            setColor(strip, Color(0, 0, 200), i, reverse, Color(0,0,40), True, False, idelay)

def fireSteps(strip, reverse=False):
    global fdelay
    if not reverse:
        for i in range(1, len(CUSTOM_STEP_LENGTH)+1):
            setColor(strip, Color(80, 200, 0), i, reverse, Color(0,50,0), True, False, fdelay) 
    else:
        for i in range(len(CUSTOM_STEP_LENGTH),0,-1):
            setColor(strip, Color(80, 200, 0), i, reverse, Color(0,50,0), True, True, fdelay)


def animation(strip, reverse):
    global ANIMATION_RUN, EFFECT,COLOR, ON
    e=4
    if EFFECT=="Switching":
        logging.info("random effect")
        e=random.randrange(1, 5)
    elif EFFECT=="Rainbow":
        e=2
    elif EFFECT=="Fire":
        e=1
    elif EFFECT=="Ice":
        e=3
    if e==1:
        logging.info("fire")
        while ANIMATION_RUN:
            fireSteps(strip, reverse)
    elif e==2:
        logging.info("rainbow")
        rainbowSteps(strip, reverse)
    elif e==3:
        logging.info("ice")
        while ANIMATION_RUN:
            iceSteps(strip, reverse)
    else:
        logging.info("color")
        setColor(strip, COLOR, None, reverse, Color(0,0,0), True, False)

def rainbowSteps(strip, reverse=False):
    if not reverse:
        for i in range(1, len(CUSTOM_STEP_LENGTH)+1):
            setColor(strip, rainbowColor(i), i, reverse, Color(0,0,0), True, False, 0.01) 
    else:
        for i in range(len(CUSTOM_STEP_LENGTH),0,-1):
            setColor(strip, rainbowColor(len(CUSTOM_STEP_LENGTH)-i), i, reverse, Color(0,0,0), True, False, 0.01)


def timeout(reverse):
    global ON, WORKING, TIMEOUT_RUN, TIMEOUT_TIME
    tt=TIMEOUT_TIME
    logging.info("timeout thread started, will trigger after: "+str(TIMEOUT_TIME))
    while TIMEOUT_RUN and tt>0:
        time.sleep(1)
        tt=tt-1
    if not WORKING.acquire(False):
        return

    if tt==0:
        logging.info("timeout after :"+str(TIMEOUT_TIME))
        clean(reverse)
    WORKING.release()


def clean(reverse):
    global ON, WORKING,ANIMATION_RUN,ANIMATION_THREAD,TIMEOUT_RUN,TIMEOUT_THREAD
    ANIMATION_RUN=False
    if ANIMATION_THREAD != None:
        ANIMATION_THREAD.join()
    setColor(strip, Color(0,0,0), None, reverse, Color(0,0,0), True, False, 0.1)
    ON=False

def movement(strip, reverse):
    global ON, WORKING,ANIMATION_RUN,ANIMATION_THREAD,TIMEOUT_THREAD, TIMEOUT_RUN,DARK
    if not WORKING.acquire(False):
        return;

    lightsoff=GPIO.input(LIGHT_PIN)
    #if lightsoff==1:
    #    strip.setBrightness(DARK_BRIGHTNESS)
    #else:
    #    strip.setBrightness(LIGHT_BRIGHTNESS)
    logging.info("movement: reverse: " + str(reverse)+" - on: "+str(ON)+" lightsoff: "+ str(lightsoff))
    if ON:
        clean(not reverse)
        TIMEOUT_RUN=False
        if TIMEOUT_THREAD != None:
            TIMEOUT_THREAD.join()
    else:
        ANIMATION_RUN=True
        ANIMATION_THREAD=Thread(target=animation, args=(strip, reverse,))
        ANIMATION_THREAD.start()
        TIMEOUT_RUN=True
        TIMEOUT_THREAD=Thread(target=timeout, args=(reverse,))
        TIMEOUT_THREAD.start()
        ON=True
    WORKING.release()




# Main program logic follows:
if __name__ == '__main__':
    # Process arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clear', action='store_true', help='clear the display on exit')
    args = parser.parse_args()
    seed(1)
    # Create NeoPixel object with appropriate configuration.
    strip = Adafruit_NeoPixel(sum(CUSTOM_STEP_LENGTH), LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    # Intialize the library (must be called once before other functions).
    strip.begin()

    logging.basicConfig(filename='/var/log/stairs.log', filemode='w', level=logging.INFO, format='%(asctime)s: %(message)s')
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(MOTION_PIN, GPIO.IN)
        GPIO.setup(MOTION2_PIN, GPIO.IN)
        GPIO.setup(LIGHT_PIN, GPIO.IN)
        CUSTOM_STEP_STARTS.append(0)
        for i in CUSTOM_STEP_LENGTH:
            CUSTOM_STEP_STARTS.append(CUSTOM_STEP_STARTS[-1]+i)
        if len(sys.argv)>2:
            setColor(strip, COLOR, int(sys.argv[1]), False, Color(0,0,0))
            clean(False)
        else:
            GPIO.add_event_detect(MOTION_PIN , GPIO.RISING, callback=lambda x : movement(strip, False), bouncetime=5000)
            GPIO.add_event_detect(MOTION2_PIN , GPIO.RISING, callback=lambda x : movement(strip, True), bouncetime=5000)
            logging.info("startup")
            while True:
                time.sleep(100)
    except:
        GPIO.cleanup()
        clean(False)
        TIMEOUT_RUN=False
        if TIMEOUT_THREAD != None:
            TIMEOUT_THREAD.join()
        logging.info(sys.exc_info()[0])
