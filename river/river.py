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

from anisodiff import *

# from config import *
# import extractors

count_prints=0

def save_img(name, img):
    global count_prints
    p=str(count_prints)+"-"+name
    cv2.imwrite(p, img)                
    count_prints=count_prints+1
    return p

    

def process_file(filepath):

    # read the image and resize it so it is faster to process
    img_original=cv2.imread(filepath, cv2.CV_LOAD_IMAGE_GRAYSCALE)

    img=cv2.imread(filepath, cv2.CV_LOAD_IMAGE_GRAYSCALE)
    height_or, width_or = img.shape

    imgcolor=cv2.imread(filepath)

    imgcolor2=cv2.imread(filepath)

    img=cv2.resize(src=img, dsize=(width_or/4, height_or/4), interpolation=cv2.INTER_AREA) 
    save_img("original.jpg", img)                


    imgcolor=cv2.resize(src=imgcolor, dsize=(width_or/4, height_or/4), interpolation=cv2.INTER_AREA)
    imgcolor2=cv2.resize(src=imgcolor2, dsize=(width_or/4, height_or/4), interpolation=cv2.INTER_AREA) 
    imgcolor3=cv2.resize(src=imgcolor2, dsize=(width_or/4, height_or/4), interpolation=cv2.INTER_AREA) 
    height, width = img.shape



    # creates black and white image
    (thresh, bw) = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY_INV)

    # fill margins with background pixels
    bw=remove_margins(bw, height, width)
         
    # get rotation of the image
    M=get_rotation(bw, height, width)
    print M

    # unrotate images
    bw = cv2.warpAffine(bw,M,(width,height))
    img = cv2.warpAffine(img,M,(width,height))
    imgcolor = cv2.warpAffine(imgcolor,M,(width,height))
    imgcolor2 = cv2.warpAffine(imgcolor2,M,(width,height))
    imgcolor3 = cv2.warpAffine(imgcolor2,M,(width,height))

    save_img("original-rotated.jpg", img)                


    # get rid of everything outside the grid
    [clean, p1, p2, p3, p4]=clean_outside_grid(img, bw, height, width, imgcolor)

    # reduce image noise
    clean = clean_noise(clean) # clean # 

    # threshold the image to start working on the inside part of the grid
    (thresh, bw) = cv2.threshold(clean, 240, 255, cv2.THRESH_BINARY_INV)

    save_img('bw-clean-external.jpg',bw)
    

    # clean up completely disconnected small areas
    bw=clean_small_regions(bw)


    #find grid lines
    [mask_v, mask_h]=find_grid(bw, height, width, imgcolor2)

    save_img('mask-vertical.jpg',mask_v)
    save_img('mask-horizontal.jpg',mask_h)


    # clean horizontal lines 
    (thresh, mask_h) = cv2.threshold(mask_h, 240, 255, cv2.THRESH_BINARY)

    w0=max(1, min(p1[0], p2[0], p3[0], p4[0])-1)
    wf=min(width, max(p1[0], p2[0], p3[0], p4[0])+1)
    h0=max(1, min(p1[1], p2[1], p3[1], p4[1])-1)
    hf=min(height, max(p1[1], p2[1], p3[1], p4[1])+1)


    save_img('bw-with-lines.jpg',bw)


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

    # get horizontal and vertical sums of bw:
    # get_sums(bw, h0, hf, w0, wf)

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

    res = cv2.bitwise_and(img,dilation)
    res2 = cv2.bitwise_or(res,cv2.bitwise_not(dilation))
    save_img('result.jpg',res2)


    M_t=cv2.invertAffineTransform(M)
    print M_t

    # M_t=cv2.getRotationMatrix2D((width/2,height/2),rot_ang,1)
    dilation_t = cv2.warpAffine(dilation,M_t,(width,height))
    save_img('bw-dilation-t.jpg',dilation_t)

    dilation_t_b =cv2.resize(src=dilation_t, dsize=(width_or, height_or), interpolation=cv2.INTER_AREA)
    res_t_b = cv2.bitwise_and(img_original,dilation_t_b)
    res2_t_b = cv2.bitwise_or(res_t_b,cv2.bitwise_not(dilation_t_b))
    save_img('result-big.jpg',res2_t_b)




    # thin the dilated image
    # thin=thin_lines(bw, w0, wf, h0, hf)
    # save_img('bw-thin.jpg',thin)


    # kernel = np.zeros((15,15),np.uint8)
    # for i in range(0, 15):
    #     kernel[12][i]=1
    # dilation = cv2.dilate(bw,kernel,iterations = 1)
    # save_img('bw-horizontal-dilation.jpg',dilation)


    (thresh, bw) = cv2.threshold(res2, 250, 255, cv2.THRESH_BINARY_INV)
    save_img('result-bw.jpg',bw)

    # # compute hough lines
    # min_line_length=10
    # max_line_gap=1
    # min_line_votes = 8
    # theta_resolution=1
    # rho=1


    # lines = cv2.HoughLinesP(image=bw, rho=rho, theta=theta_resolution*math.pi/180, threshold=min_line_votes, minLineLength=min_line_length, maxLineGap=max_line_gap)
    # mask_v = np.zeros(bw.shape,np.uint8)
    # mask_h = np.zeros(bw.shape,np.uint8)

    # print lines[0]

    # for x1,y1,x2,y2 in lines[0]:
    #     ang = math.degrees(math.atan2((y2-y1),(x2-x1)))
    #     print ang
    #     if(ang>=85 or ang<=-85): #vertical lines
    #         cv2.line(mask_v,(x1,y1),(x2,y2),(255,255,255),1)
    #         cv2.line(res2,(x1,y1),(x2,y2),(0, 255,0),2)
    #     elif(ang>=-5 and ang<=5): #horizontal lines
    #         cv2.line(mask_h,(x1,y1),(x2,y2),(255,255,255),1)
    #         cv2.line(res2,(x1,y1),(x2,y2),(0,255,0),2)

    # save_img('result-lines.jpg',res2)
    # save_img('mask-vertical.jpg',mask_v)
    # save_img('mask-horizontal.jpg',mask_h)


    contours, hierarchy = cv2.findContours(bw,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)

    for cnt in contours:
        cv2.drawContours(imgcolor3,[cnt],0,(255,0,0),-1)

    save_img('result-contours.jpg',imgcolor3)



def thin_lines(dilation, w0, wf, h0, hf):

    (thresh, thin) = cv2.threshold(dilation, 240, 255, cv2.THRESH_BINARY)
    save_img('before-thin.jpg',thin)

    # print np.max(thin)
        
    # print w0, wf
    # print h0, hf

    THINNING = True

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
    min_line_length=int(0.4*width)+1
    max_line_gap=int(0.001*width)+1
    min_line_votes = int(0.4*width)+1
    theta_resolution=1
    rho=1


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

    save_img("dilation-before-clean-outside.jpg", dilation)                

    # find contours
    contours, hierarchy = cv2.findContours(dilation,cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE)

    for cnt in contours:
        if cv2.contourArea(cnt)<500:
            cv2.drawContours(bw,[cnt],0,(0,0,0),-1)

    save_img('bw-before-clean-outside.jpg',bw)


    # dilate ink to make it easier to find lines
    kernel = np.ones((3,3),np.uint8)
    dilation = cv2.dilate(bw,kernel,iterations = 3)

    save_img("dilation-before-clean-outside-2.jpg", dilation)                

    # compute hough lines
    min_line_length=int(0.8*width)+1
    max_line_gap=int(0.001*width)+1
    min_line_votes = int(0.6*width)+1
    theta_resolution=1
    rho=1

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
        # else:
        #     # print ang
        #     if imgcolor is not None:
        #         cv2.line(imgcolor,(x1,y1),(x2,y2),(0,0,255),2)

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

    # print "vertical slopes: ", mv_min, mv_max
    # print "horizontal slopes: ", mh_min, mh_max

    # top left
    if mv_min==0:
        x = x1v_min
        y = mh_min *(x-x1h_min) + y1h_min

    else:
        x = ((mv_min*x1v_min) - (mh_min*x1h_min) + (y1h_min - y1v_min))/ (mv_min -mh_min)
        y = mv_min *(x-x1v_min) + y1v_min

    p1 = [int(x), int(y)]

    # top right 
    if mv_max==0:
        x = x1v_max
        y = mh_min *(x-x1h_min) + y1h_min

    else:
        x = ((mv_max*x1v_max) - (mh_min*x1h_min) + (y1h_min - y1v_max))/ (mv_max -mh_min)
        y = mv_max *(x-x1v_max) + y1v_max

    p2 = [int(x), int(y)]

    # bottom left
    if mv_min==0:
        x = x1v_min
        y = mh_max *(x-x1h_max) + y1h_max

    else:
        x = ((mv_min*x1v_min) - (mh_max*x1h_max) + (y1h_max - y1v_min))/ (mv_min -mh_max)
        y = mv_min *(x-x1v_min) + y1v_min

    p3 = [int(x), int(y)]

    # bottom right
    if mv_max==0:
        x = x1v_max
        y = mh_max *(x-x1h_max) + y1h_max

    else:
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
    save_img('no-external-grid.jpg',res2)

    return [res2, p1, p2, p3, p4]


def clean_small_regions(bw):

    kernel = np.ones((3,3),np.uint8)

    dilation = cv2.dilate(bw,kernel,iterations = 1)
    save_img('dilation-clean.jpg',dilation)

    bw = clean_by_area(dilation, bw)
    save_img('bw-clean.jpg',bw)

    dilation = cv2.dilate(bw,kernel,iterations = 2)
    save_img("dilation-clean.jpg", dilation)                

    bw = clean_by_area(dilation, bw)
    save_img('bw-clean.jpg',bw)

    dilation = cv2.dilate(bw,kernel,iterations = 1)
    save_img('dilation-clean.jpg',dilation)

    bw = clean_by_area(dilation, bw)
    save_img('bw-clean.jpg',bw)

    return bw

def clean_by_area(dilation, bw):

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

def find_grid(bw, height, width, imgcolor2=None):

    # compute hough lines
    min_line_length=int(0.2*width)+1
    max_line_gap=int(0.01*width)+1
    min_line_votes = int(0.1*width)+1
    theta_resolution=1
    rho=1

    #clean up non-line elements
    kernel = np.ones((3,3),np.uint8)
    dilation = cv2.dilate(bw,kernel,iterations = 3)
    save_img('dilation-for-grid.jpg',dilation)


    lines = cv2.HoughLinesP(image=dilation, rho=rho, theta=theta_resolution*math.pi/180, threshold=min_line_votes, minLineLength=min_line_length, maxLineGap=max_line_gap)
    mask_v = np.zeros(bw.shape,np.uint8)
    mask_h = np.zeros(bw.shape,np.uint8)

    for x1,y1,x2,y2 in lines[0]:
        ang = math.degrees(math.atan2((y2-y1),(x2-x1)))

        if(ang>=85 or ang<=-85): #vertical lines
            cv2.line(mask_v,(x1,y1),(x2,y2),(255,255,255),2)
            if imgcolor2 is not None:
                cv2.line(imgcolor2,(x1,y1),(x2,y2),(255,0,0),2)
        elif(ang>=-5 and ang<=5): #horizontal lines
            cv2.line(mask_h,(x1,y1),(x2,y2),(255,255,255),2)
            if imgcolor2 is not None:
                cv2.line(imgcolor2,(x1,y1),(x2,y2),(0,255,0),2)


    if imgcolor2 is not None:
        save_img('houghlines.jpg',imgcolor2)

    return [mask_v, mask_h]


def find_grid_old(bw, height, width, imgcolor2=None):

    # compute hough lines
    min_line_length=int(0.6*width)+1
    max_line_gap=int(0.1*width)+1
    min_line_votes = int(0.4*width)+1
    theta_resolution=1
    rho=1

    #clean up non-line elements
    kernel = np.ones((3,3),np.uint8)
    dilation = cv2.dilate(bw,kernel,iterations = 3)
    save_img('dilation-for-grid.jpg',dilation)


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

        if(ang>=85 or ang<=-85): #vertical lines
            cv2.line(mask_v,(x1,y1),(x2,y2),(255,255,255),2)
            if imgcolor2 is not None:
                cv2.line(imgcolor2,(x1,y1),(x2,y2),(255,0,0),2)
        elif(ang>=-5 and ang<=5): #horizontal lines
            cv2.line(mask_h,(x1,y1),(x2,y2),(255,255,255),2)
            if imgcolor2 is not None:
                cv2.line(imgcolor2,(x1,y1),(x2,y2),(0,255,0),2)

        # else:
        #     if imgcolor2 is not None:
        #         cv2.line(imgcolor2,(x1,y1),(x2,y2),(0,0,255),2)


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

def clean_noise(img):

    img=anisodiff(img=img, niter=15, option=1)
    p=save_img("original-denoised.jpg", img)     
    img=cv2.imread(p, cv2.CV_LOAD_IMAGE_GRAYSCALE)           

    return img

    # img=cv2.bilateralFilter(src=img,d=15,sigmaColor=105,sigmaSpace=105)

    # img=cv2.bilateralFilter(src=img,d=15,sigmaColor=75,sigmaSpace=75)
    # img=cv2.fastNlMeansDenoising(src=img, dst=None, h=20, templateWindowSize=5, searchWindowSize=15)


    # img2=cv2.Laplacian(img, 3)
    # save_img("edges.jpg", img2)


def matchLines(template_lines, image_lines, max_translation, min_scale, max_scale):
    lines = []
    mina = 1
    minb = 0
    min_cost=sys.maxint

    for tl in template_lines:
        for il in image_lines:
        
            if(abs(tl-il) < max_translation):
                for tl2 in template_lines:
                    for il2 in image_lines:
                        a = (il2-il) / (1.0*(tl2-tl))
                        b = -a * tl + il
                            
                        if(a > min_scale and a < max_scale and abs(b) < max_translation):
                            lines=[]
                            
                            for i in template_lines:
                                lines.append(int(a*i + b))

                                cost = dtwDistance(lines, image_lines)
                            
                            if(cost < min_cost):
                                min_cost = cost
                                mina = a
                                minb = b

    
    print "Scale: " , mina , ", Translation: " , minb
    
    lines=[]    
    for tl in template_lines:
        lines.append(int(mina*tl + minb))
    
            
    return lines


def dtwDistance( a,  b):
    d = np.zeros((len(a)+1, len(b)+1))
           
    for i in range(1, len(a)):
        d[i][0] = sys.maxint
    
    for j in range(1, len(b)):
        d[0][j] = sys.maxint
    
    for i in range(1, len(a)):
        for j in range(1, len(b)):
            tmpd = abs(a[i-1]-b[j-1])
            d0 = d[i-1][j]         #Deletion
            d1 = d[i][j-1]         #Insertion
            d2 = d[i-1][j-1]       #Match/Substitution
            
            d[i][j] = tmpd + min(d0, d1, d2)
    
    return int(d[len(a)][len(b)])


def get_sums(bw, h0, hf, w0, wf):
    sums=[]
    for row in range(h0, hf, 1):
        c=0
        for col in range(w0, wf, 1):
            if not (bw[row, col]==0):
                c=c+1
        sums.append(c)

    hor_sum = np.zeros(bw.shape,np.uint8)
    # print "shape hor_sum: ", hor_sum.shape
    # print "shape sums: ", len(sums)
    # print "shape sums should be: ", (hf-h0)
    c=0
    for row in range(h0, hf, 1):
        # print row, ",", sums[c]

        for i in range(0, sums[c]):
            cv2.line(hor_sum,(i,row),(i,row),(255,255,255),1)
            # hor_sum[row, i]=1
        c=c+1

    save_img("horizontal-sums.jpg", hor_sum)                


    sums=[]
    for col in range(w0, wf, 1):
        c=0
        for row in range(h0, hf, 1):
            if not (bw[row, col]==0):
                c=c+1
        sums.append(c)

    vert_sum = np.zeros(bw.shape,np.uint8)
    c=0
    for col in range(w0, wf, 1):
        # print row, ",", sums[c]

        for i in range(0, sums[c]):
            cv2.line(vert_sum,(col, i),(col, i),(255,255,255),1)
            # hor_sum[row, i]=1
        c=c+1

    save_img("vertical-sums.jpg", vert_sum)                

    return


def main():

    filepath="./TerEx_demo_1820s_str/39-44.tif"
    # filepath="./TerEx_demo_1820s_str/39-45.tif"
    # filepath="./TerEx_demo_1820s_str/39-71.tif"
    # filepath="./TerEx_demo_1820s_str/39-72.tif"

    process_file(filepath)
    




if __name__ == "__main__":
    main()


