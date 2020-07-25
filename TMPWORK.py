# CODE FOR METADATA EXTRACTION
## ffmpeg -i input.mp4 -c copy -map_metadata 0 -map_metadata:s:v 0:s:v -map_metadata:s:a 0:s:a -f ffmetadata output.txt
import subprocess
import os
import pandas as pd
import pytesseract
from PIL import Image
import re
import cv2
import numpy as np

def get_creation_time(file_name):
    
    subprocess.call([
        'ffmpeg',
        '-i',
        file_name,
        '-c',
        'copy',
        '-map_metadata',
        '0',
        '-map_metadata:s:v',
        '0:s:v',
        '-map_metadata:s:a',
        '0:s:a',
        '-f',
        'ffmetadata',
        'output.txt']
    )
    try:
        text  = pd.read_csv('output.txt', sep = '=',index_col= 0)
    except:
        print('Error in video!')
        return None
    time = (text.loc['creation_time'][0])
    os.remove('output.txt')
    time = time.split('T')
    date, time = time[0], time[1]
    time = time.replace('Z','')
    return date, time

# CODE FOR FRAME EXTRACTION
## ffmpeg -i input.mp4  -ss 0 -frames 1 -r 1 -f image2 frame%03d.jpeg

def get_first_frame(file_name, output):
    subprocess.call([
        'ffmpeg',
        '-i',
        file_name,
        '-ss',
        '0',
        '-frames',
        '1',
        '-r',
        '1',
        '-f',
        'image2',
        output
    ])

def get_timecode(file_name):
    get_first_frame(file_name, 'frame.jpg')
    im = Image.open('frame.jpg')
    w, h = im.size
    right = w * 4/10
    bottom = h * 1/15
    im1 = im.crop((0,0,right,bottom))
    # im1.show()
    ret,img = cv2.threshold(np.array(im1), 125, 255, cv2.THRESH_BINARY)
    img = Image.fromarray(img.astype(np.uint8))
    width, height = img.size[0], img.size[1]
    img = img.resize((500,int((500)/width * height)),Image.ANTIALIAS)
    ocr_result = pytesseract.image_to_string(img, lang='eng',config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789-:.')
    # img.show()
    os.remove('frame.jpg')
    # print(ocr_result)
    #insert code to split up timecode
    ocr_result = re.split('[:-]',ocr_result)
    date = ocr_result[0][-4:] + '-' + ocr_result[1]+'-' + ocr_result[2][0:2]
    time = ocr_result[2][-2:] + ':' + ocr_result[3] + ':' + ocr_result[4][0:2]
    return date, time

def get_time_diff(datetime1,datetime2):
    date1, time1 = datetime1[0], datetime1[1]
    date2, time2 = datetime2[0], datetime2[1]
    time1, time2 = time1.split(':'), time2.split(':')
    # step 1: assert that it is the same date.
    if date1 != date2:
        print('These clips happened on different days!')
        return None
    # step 2: find which one is the later timestamp (and thus the timestamp to remain unchanged)
    # only checks hour for issues, they should be the same
    if time1[0] != time2[0]:
        print('The videos are off by an hour. This doesnt make sense, and is probably due to daylight savings issues')
        return None
    compTime1 = float(time1[1]) * 60 + float(time1[2])
    compTime2 = float(time2[1])*60 + float(time2[2])
    timeshift = (compTime1 - compTime2)
    if timeshift < 0:
        syncedTime = datetime2[1]
        timeshift= abs(timeshift)
    else:
        syncedTime = datetime1[1]
    return syncedTime, timeshift

def get_time_diff_multiple(dateTimes):
    #Assert all of these happens on the same day
    testTime = dateTimes[0][0]
    dayStatus = [True if n[0] == testTime else False for n in dateTimes]
    if False in dayStatus:
        print('Some of these videos happen on different days!')
        return None
    compTimes = [float((n[1].split(':'))[1])*60 + float((n[1].split(':'))[2]) for n in dateTimes]
    setTime = max(compTimes)
    timeShifts = [setTime - n for n in compTimes]
    return timeShifts

def shift_by(video,time,output):
    # Code to crop start
    ## ffmpeg -i in.mp4 -ss 64 -c:v libx264 out.mp4
    # Code to add black frames
 
    # ffmpeg -i test.mp4 -f lavfi -i "color=c=black:s=640x480:r=25:sar=0/1" -filter_complex \
    # "[0:v] setpts=PTS-STARTPTS [main]; \
    # [1:v] trim=end=10,setpts=PTS-STARTPTS [pre]; \
    # [1:v] trim=end=30,setpts=PTS-STARTPTS [post]; \
    # [pre][main][post] concat=n=3:v=1:a=0 [out]" \
    # -map "[out]" -vcodec mpeg2video -maxrate 30000k -b:v 30000k output.mp4
    subprocess.call([
        'ffmpeg',
        '-i',
        video,
        '-ss',
        str(time),
        '-c:v',
        'libx264', #can't be copy, the times are off by too much i think. can be tested per machine.
        output
    ])

def add_black_frames(video,before,after):
    ## add support for multiple ratios and resolutions
    ## 
    # ffmpeg -i input -f lavfi -i "color=c=black:s=720x576:r=25:sar=1023/788" -filter_complex \
    # "[0:v] setpts=PTS-STARTPTS [main]; \
    #  [1:v] trim=end=10,setpts=PTS-STARTPTS [pre]; \
    #  [1:v] trim=end=30,setpts=PTS-STARTPTS [post]; \
    #  [pre][main][post] concat=n=3:v=1:a=0 [out]" \
    # -map "[out]" -vcodec mpeg2video -maxrate 30000k -b:v 30000k output.mpg
    subprocess.call([
        'ffmpeg', '-i', video, '-f', 'lavfi','-i', 'color=c=black:s=640x480:r=25:sar=0/1','-filter_complex','[0:v] setpts=PTS-STARTPTS [main]; [1:v] trim=end='+ str(before) +',setpts=PTS-STARTPTS [pre]; [1:v] trim=end='+str(after)+',setpts=PTS-STARTPTS [post]; [pre][main][post] concat=n=3:v=1:a=0 [out]','-map','[out]', 
        '-vcodec', 'libx264', '-maxrate', '30000k', '-b:v', '30000k', 'output.mp4'
    ])

def get_res(video):
    # ffmpeg -i video.mp4 2>&1 | grep Video: | grep -Po '\d{3,5}x\d{3,5}'
    subprocess.Popen(['ffmpeg', '-i', 'Resources/videos/test.mp4', '2>&1','|', 'grep', 'Video:','|','grep', '-Po', '\d{3,5}x\d{3,5}'])

def get_length(filename):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    return float(result.stdout)

if __name__ == "__main__":
    # add_black_frames('Resources/videos/test.mp4',10,30)
    # get_res(None)
    print(get_length('Resources/videos/test.mp4'))
    # TODO: map shifts to a video files, so you can get which is mapped to annotations


