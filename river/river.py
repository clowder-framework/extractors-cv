#!/usr/bin/env python
import pika
import sys
import json
import traceback
import requests
import tempfile
import subprocess
import os
import itertools
import numpy as np
import cv2
import time
import math
import operator

# from config import *
# import extractors

count_prints=0

def save_img(name, img):
    global count_prints
    cv2.imwrite(str(count_prints)+"-"+name, img)                
    count_prints=count_prints+1

    

def process_file(filepath):

    # read the image and resize it so it is faster to process
    img=cv2.imread(filepath, cv2.CV_LOAD_IMAGE_GRAYSCALE)
    height, width = img.shape

    imgcolor=cv2.imread(filepath)

    imgcolor2=cv2.imread(filepath)

    img=cv2.resize(src=img, dsize=(width/4, height/4), interpolation=cv2.INTER_AREA) 
    imgcolor=cv2.resize(src=imgcolor, dsize=(width/4, height/4), interpolation=cv2.INTER_AREA)
    imgcolor2=cv2.resize(src=imgcolor2, dsize=(width/4, height/4), interpolation=cv2.INTER_AREA) 
    height, width = img.shape


    save_img("original.jpg", img)                

    # creates black and white image
    (thresh, bw) = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY_INV)

    # fill margins with background pixels
    bw=remove_margins(bw, height, width)
         
    # get rotation of the image
    M=get_rotation(bw, height, width)

    # unrotate images
    bw = cv2.warpAffine(bw,M,(width,height))
    img = cv2.warpAffine(img,M,(width,height))
    imgcolor = cv2.warpAffine(imgcolor,M,(width,height))
    imgcolor2 = cv2.warpAffine(imgcolor2,M,(width,height))

    save_img("original-rotated.jpg", img)                



    # get rid of everything outside the grid
    [clean, p1, p2, p3, p4]=clean_outside_grid(img, bw, height, width, imgcolor)


    # threshold the image to start working on the inside part of the grid
    (thresh, bw) = cv2.threshold(clean, 240, 255, cv2.THRESH_BINARY_INV)

    save_img('bw-clean-external.jpg',bw)
    

    # clean up completely disconnected small areas
    kernel = np.ones((3,3),np.uint8)
    dilation = cv2.dilate(bw,kernel,iterations = 2)
    save_img("dilation.jpg", dilation)                

    bw = clean_small_regions(dilation, bw)
    save_img('bw-clean.jpg',bw)

    dilation = cv2.dilate(bw,kernel,iterations = 1)
    save_img('dilation-clean.jpg',dilation)

    bw = clean_small_regions(dilation, bw)
    save_img('bw-clean.jpg',bw)


    #find grid lines
    [mask_v, mask_h]=find_grid(bw, dilation, height, width, imgcolor2)

    save_img('mask-vertical.jpg',mask_v)
    save_img('mask-horizontal.jpg',mask_h)


    # clean horizontal lines 
    (thresh, mask_h) = cv2.threshold(mask_h, 240, 255, cv2.THRESH_BINARY)

    w0=max(1, min(p1[0], p2[0], p3[0], p4[0])-1)
    wf=min(width, max(p1[0], p2[0], p3[0], p4[0])+1)
    h0=max(1, min(p1[1], p2[1], p3[1], p4[1])-1)
    hf=min(height, max(p1[1], p2[1], p3[1], p4[1])+1)


    for col in range(w0, wf, 1):
        for row in range(h0, hf, 1):
            if mask_h[row, col]==255:
                # if bw[row-1, col]==0 and bw[row+1, col]==0 and bw[row, col-1]==0 and bw[row, col+1]==0:
                if bw[row-1, col]==0:# and bw[row-1, col-1]==0:# and bw[row-1, col+1]==0:
                    bw[row, col]=0

    save_img('clean-horizontal.jpg',bw)

    # clean vertical lines 
    (thresh, mask_v) = cv2.threshold(mask_v, 240, 255, cv2.THRESH_BINARY)

    for row in range(h0, hf, 1):
        for col in range(w0, wf, 1):
            if mask_v[row, col]==255:
                # if bw[row-1, col]==0 and bw[row+1, col]==0 and bw[row, col-1]==0 and bw[row, col+1]==0:
                if bw[row, col-1]==0:# and bw[row-1, col-1]==0:#  and bw[row+1, col-1]==0 :
                    bw[row, col]=0

    save_img('clean-vertical.jpg',bw)



    #clean up very small elements

    kernel = np.ones((3,3),np.uint8)
    dilation = cv2.dilate(bw,kernel,iterations = 1)

    save_img("dilation.jpg", dilation)                

    # find contours
    contours, hierarchy = cv2.findContours(dilation,cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE)

    for cnt in contours:
        if cv2.contourArea(cnt)<20:
            cv2.drawContours(bw,[cnt],0,(0,0,0),-1)

    save_img('bw-clean.jpg',bw)


    kernel = np.ones((5,5),np.uint8)
    dilation = cv2.dilate(bw,kernel,iterations = 1)
    save_img('bw-dilation.jpg',dilation)


    dilation = cv2.dilate(dilation,kernel,iterations = 1)
    save_img('bw-dilation.jpg',dilation)


    contours, hierarchy = cv2.findContours(dilation,cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE)
    # cnts = sorted(contours, key = cv2.contourArea, reverse = True)[:10]
    areas = [cv2.contourArea(cnt) for cnt in contours]
    # print areas
    areas_mean=np.mean(areas)
    # print "mean areas:", areas_mean
    areas_median= np.median(areas)
    # print "median areas:", areas_median

    for cnt in contours:
        if cv2.contourArea(cnt)<2*areas_median:
            cv2.drawContours(bw,[cnt],0,(0,0,0),-1)

    save_img('bw-clean.jpg',bw)

    for cnt in contours:
        # print cv2.contourArea(cnt)
        
        x,y,w,h = cv2.boundingRect(cnt)
        
        if (1.0*cv2.contourArea(cnt))/(w*h)>0.7:
            cv2.drawContours(bw,[cnt],0,(0,0,0),-1)

    save_img('bw-clean.jpg',bw)


    for cnt in contours:
        if cv2.contourArea(cnt)<areas_mean:
            cv2.drawContours(bw,[cnt],0,(0,0,0),-1)


    save_img('bw-clean.jpg',bw)

    dilation = cv2.dilate(bw,kernel,iterations = 2)
    save_img('bw-dilation.jpg',dilation)

    # thin the dilated image
    thin=thin_lines(dilation)
    save_img('bw-thin.jpg',thin)


def thin_lines(dilation):

    (thresh, thin) = cv2.threshold(dilation, 240, 255, cv2.THRESH_BINARY)
    save_img('bw-thin.jpg',thin)

    print np.max(thin)

    THINNING = True
        
    print w0, wf
    print h0, hf

    while(THINNING):
        THINNING = False

        for h in range(h0, hf, 1):
            for w in range(w0, wf, 1):

                if(thin[h, w] > 0):
                    
                    if  ((thin[h-1, w-1]>0  and   thin[h, w-1]>0    and   thin[h+1, w-1]>0)  or   # left
                         (thin[h, w-1]>0    and   thin[h+1, w-1]>0  and   thin[h+1, w]>0)    or   # bottom left
                         (thin[h+1, w-1]>0  and   thin[h+1, w]>0    and   thin[h+1, w+1]>0)  or   # bottom
                         (thin[h+1, w]>0    and   thin[h+1, w+1]>0  and   thin[h, w+1]>0)    or   # bottom right
                         (thin[h+1, w+1]>0  and   thin[h, w+1]>0    and   thin[h-1, w+1]>0)  or   # right
                         (thin[h, w+1]>0    and   thin[h-1, w+1]>0  and   thin[h-1, w]>0)    or   # top right
                         (thin[h-1, w+1]>0  and   thin[h-1, w]>0    and   thin[h-1, w-1]>0)  or   # top
                         (thin[h-1, w]>0    and   thin[h-1, w-1]>0  and   thin[h, w-1]>0)):       # top left
                            
                        thin[h, w] = 0
                        THINNING = True 

    return thin

def get_rotation(bw, height, width):

    # dilate ink to make it easier to find lines
    kernel = np.ones((3,3),np.uint8)
    dilation = cv2.dilate(bw,kernel,iterations = 1)

    save_img("dilation-get-rotation.jpg", dilation)                

    # compute hough lines
    min_line_length=int(0.4*width)+1;
    max_line_gap=int(0.001*width)+1;
    min_line_votes = int(0.4*width)+1;
    theta_resolution=1;
    rho=1;


    lines = cv2.HoughLinesP(image=dilation, rho=rho, theta=theta_resolution*math.pi/180, threshold=min_line_votes, minLineLength=min_line_length, maxLineGap=max_line_gap)
    angs = []
    for x1,y1,x2,y2 in lines[0]:
        ang = math.degrees(math.atan2((y2-y1),(x2-x1)))
        if(ang>=-20 and ang<=20): #horizontal lines
            angs.append(ang)

    ang = int(np.median(angs))


    M = cv2.getRotationMatrix2D((width/2,height/2),ang,1)

    return M



def remove_margins(bw, height, width):
    for row in range(height):
        for col in range(width):
            if bw[row, col]==255:
                bw[row, col]=0
            else:
                break

    for row in range(height):
        for col in range(width-1, -1, -1):
            if bw[row, col]==255:
                bw[row, col]=0
            else:
                break

    for col in range(width):
        for row in range(height):
            if bw[row, col]==255:
                bw[row, col]=0
            else:
                break

    for col in range(width):
        for row in range(height-1, -1, -1):
            if bw[row, col]==255:
                bw[row, col]=0
            else:
                break

    save_img("bw-no-margins.jpg", bw)
    return bw


def clean_outside_grid(img, bw, height, width, imgcolor=None):

    #clean up non-line elements
    kernel = np.ones((3,3),np.uint8)
    dilation = cv2.dilate(bw,kernel,iterations = 1)

    save_img("dilation-clean-outside.jpg", dilation)                

    # find contours
    contours, hierarchy = cv2.findContours(dilation,cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE)

    for cnt in contours:
        if cv2.contourArea(cnt)<500:
            cv2.drawContours(bw,[cnt],0,(0,0,0),-1)

    save_img('bw-before-clean-outside.jpg',bw)


    # dilate ink to make it easier to find lines
    kernel = np.ones((3,3),np.uint8)
    dilation = cv2.dilate(bw,kernel,iterations = 3)

    save_img("dilation-rotated.jpg", dilation)                

    # compute hough lines
    min_line_length=int(0.8*width)+1;
    max_line_gap=int(0.001*width)+1;
    min_line_votes = int(0.6*width)+1;
    theta_resolution=1;
    rho=1;

    lines = cv2.HoughLinesP(image=dilation, rho=rho, theta=theta_resolution*math.pi/180, threshold=min_line_votes, minLineLength=min_line_length, maxLineGap=max_line_gap)
 
    # find limiting lines
    vert_x_min=width
    vert_x_max=-1
    hori_y_min=height
    hori_y_max=-1


    for x1,y1,x2,y2 in lines[0]:
        ang = math.degrees(math.atan2((y2-y1),(x2-x1)))

        if(ang>=70 or ang<=-70): #vertical lines
            if imgcolor is not None:
                cv2.line(imgcolor,(x1,y1),(x2,y2),(255,0,0),2)
            if(x1 < vert_x_min) or (x2 < vert_x_min):
                vert_min=[x1, y1, x2, y2]
                vert_x_min = min(x1, x2)
            if(x1 > vert_x_max) or (x2 > vert_x_max):
                vert_max=[x1, y1, x2, y2]
                vert_x_max = max(x1, x2)
        elif(ang>=-20 and ang<=20): #horizontal lines
            if imgcolor is not None:
                cv2.line(imgcolor,(x1,y1),(x2,y2),(0,255,0),2)
            if(y1 < hori_y_min) or (y2 < hori_y_min):
                hori_min=[x1, y1, x2, y2]
                hori_y_min = min(y1, y2)
            if(y1 > hori_y_max) or (y2 > hori_y_max):
                hori_max=[x1, y1, x2, y2]
                hori_y_max = max(y1, y2)
        else:
            # print ang
            if imgcolor is not None:
                cv2.line(imgcolor,(x1,y1),(x2,y2),(0,0,255),2)

    if imgcolor is not None:      
        save_img('houghlines.jpg',imgcolor)

    # vertical line limits
    if(vert_min[2]==vert_min[0]):
        mv_min=0
    else:
        mv_min = (vert_min[3]-vert_min[1])*1.0/(vert_min[2]-vert_min[0])
    x1v_min = vert_min[0]
    y1v_min = vert_min[1]

    if(vert_max[2]==vert_max[0]):
        mv_max=0
    else:
        mv_max = (vert_max[3]-vert_max[1])*1.0/(vert_max[2]-vert_max[0])
    x1v_max = vert_max[0]
    y1v_max = vert_max[1]

    # horizontal line limits    
    if(hori_min[2]==hori_min[0]):
        mh_min=0
    else:
        mh_min = (hori_min[3]-hori_min[1])*1.0/(hori_min[2]-hori_min[0])
    x1h_min = hori_min[0]
    y1h_min = hori_min[1]

    if(hori_max[2]==hori_max[0]):
        mh_max=0
    else:
        mh_max = (hori_max[3]-hori_max[1])*1.0/(hori_max[2]-hori_max[0])
    x1h_max = hori_max[0]
    y1h_max = hori_max[1]
    

    # find intercept points

    print "vertical slopes: ", mv_min, mv_max
    print "horizontal slopes: ", mh_min, mh_max

    # top left
    x = ((mv_min*x1v_min) - (mh_min*x1h_min) + (y1h_min - y1v_min))/ (mv_min -mh_min)
    y = mv_min *(x-x1v_min) + y1v_min

    p1 = [int(x), int(y)]

    # top right 
    x = ((mv_max*x1v_max) - (mh_min*x1h_min) + (y1h_min - y1v_max))/ (mv_max -mh_min)
    y = mv_max *(x-x1v_max) + y1v_max

    p2 = [int(x), int(y)]

    # bottom left
    x = ((mv_min*x1v_min) - (mh_max*x1h_max) + (y1h_max - y1v_min))/ (mv_min -mh_max)
    y = mv_min *(x-x1v_min) + y1v_min

    p3 = [int(x), int(y)]

    # bottom right
    x = ((mv_max*x1v_max) - (mh_max*x1h_max) + (y1h_max - y1v_max))/ (mv_max -mh_max)
    y = mv_max *(x-x1v_max) + y1v_max

    p4 = [int(x), int(y)]


    points = np.array([p1, p2, p3, p4])

    # compute the convex hull that contains all the lines endpoints
    hull = cv2.convexHull(points,returnPoints = True)

    # compute the contour of the hull
    cnts = np.reshape(hull, (1, -1, 2))
    
    if imgcolor is not None:
        cv2.drawContours(imgcolor,cnts,-1,(255,0,0),-1)
        save_img('hull.jpg',imgcolor)

    # eliminates everything out of the hull from the image
    mask = np.zeros(bw.shape,np.uint8)
    cv2.drawContours(mask,cnts,-1,255,-1)
    save_img('mask.jpg',mask)

    res = cv2.bitwise_and(img,mask)
    res2 = cv2.bitwise_or(res,cv2.bitwise_not(mask))
    save_img('res.jpg',res2)

    return [res2, p1, p2, p3, p4]


def clean_small_regions(dilation, bw):

    contours, hierarchy = cv2.findContours(dilation,cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE)

    areas = [cv2.contourArea(cnt) for cnt in contours]
    # print areas
    areas_mean=np.mean(areas)
    # print "mean areas:", areas_mean
    areas_median= np.median(areas)
    # print "median areas:", areas_median

    for cnt in contours:
        if cv2.contourArea(cnt)<areas_mean:
            cv2.drawContours(bw,[cnt],0,(0,0,0),-1)

    return bw

def find_grid(bw, dilation, height, width, imgcolor2=None):
    # compute hough lines
    min_line_length=int(0.6*width)+1;
    max_line_gap=int(0.1*width)+1;
    min_line_votes = int(0.4*width)+1;
    theta_resolution=1;
    rho=1;

    lines = cv2.HoughLinesP(image=dilation, rho=rho, theta=theta_resolution*math.pi/180, threshold=min_line_votes, minLineLength=min_line_length, maxLineGap=max_line_gap)
    mask_v = np.zeros(bw.shape,np.uint8)
    mask_h = np.zeros(bw.shape,np.uint8)

    # get period of the lines
    # vert_col = []
    # hori_row = []

    # for x1,y1,x2,y2 in lines[0]:
    #     ang = math.degrees(math.atan2((y2-y1),(x2-x1)))

    #     if(ang>=70 or ang<=-70): #vertical lines
    #         vert_col.append(x1)
    #     elif(ang>=-20 and ang<=20): #horizontal lines
    #         hori_row.append(y1)

    # vert_period_thresh=0.9*get_period(vert_col)

    # hori_period_thresh=0.9*get_period(hori_row)


    # hori_final=[filtered_hori_row[0]]
    # for e in filtered_hori_row:
    #     if(e-hori_final[-1]>=hori_period_thresh):
    #         hori_final.append(e)



    for x1,y1,x2,y2 in lines[0]:
        ang = math.degrees(math.atan2((y2-y1),(x2-x1)))

        if(ang>=70 or ang<=-70): #vertical lines
            cv2.line(mask_v,(x1,y1),(x2,y2),(255,255,255),2)
            if imgcolor2 is not None:
                cv2.line(imgcolor2,(x1,y1),(x2,y2),(255,0,0),2)
        elif(ang>=-20 and ang<=20): #horizontal lines
            cv2.line(mask_h,(x1,y1),(x2,y2),(255,255,255),2)
            if imgcolor2 is not None:
                cv2.line(imgcolor2,(x1,y1),(x2,y2),(0,255,0),2)

        else:
            if imgcolor2 is not None:
                cv2.line(imgcolor2,(x1,y1),(x2,y2),(0,0,255),2)


    if imgcolor2 is not None:
        save_img('houghlines.jpg',imgcolor2)

    return [mask_v, mask_h]


def get_period(lines):

    lines=sorted(lines)

    filtered_lines=[]
    curr=lines[0]
    fl=[lines[0]]
    for l in lines:
        if not (l-curr<3) and not (l==curr):
            print "fl: ", fl
            print np.median(fl)
            filtered_lines.append(sorted(fl)[len(fl)/2])
            fl=[]
        if not (l==curr):
            fl.append(l)
        curr=l

    if fl:
        filtered_lines.append(sorted(fl)[len(fl)/2])

    dist=[]
    for i in range(0, len(filtered_lines)-1):
        dist.append(filtered_lines[i+1]-filtered_lines[i])

    return np.mean(dist)

def main():

    filepath="./TerEx_demo_1820s_str/39-44.tif"
    # filepath="./TerEx_demo_1820s_str/39-45.tif"
    # filepath="./TerEx_demo_1820s_str/39-71.tif"
    # filepath="./TerEx_demo_1820s_str/39-72.tif"

    process_file(filepath)
    




if __name__ == "__main__":
    main()


