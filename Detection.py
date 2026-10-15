import cv2
import numpy as np
import os

#Configuration-----------------------------------------------------------------------------
cameraIndex=0; #Support maximum of 2 according to MindVision 
initialPicture=""; #Reference Picture

#To be Manually Set 
CENTER_X=None;
CENTER_Y=None;
RADIUS=None; 

#Comparison Parameter
BlurSize=5;
thresholdValue=25;
StandardMINArea=20; #comparion area; adjust to improve accuracy
#------------------------------------------------------------------------------------------
#Disk Mask 
def disk_mask(image): 
    height, width =image.shape[:2];
    center_x= CENTER_X if CENTER_X is not None else CENTER_X//2;
    center_y= CENTER_Y if CENTER_Y is not None else CENTER_Y//2;
    radius= RADIUS if RADIUS is not None else int(
        min(height,width)*0.45
    )

    mask=np.zeros((height,width),dtype=np.unit8);
    cv2.circle(int(center_x),int(center_y),int(radius),255,-1);

    return mask, (int(center_x),int(center_y),int(radius));

#Comparison
def detection(frame,reference, mask):
    current_gray= cv2.cvtColor(frame,cv2.COLOR_BRT2GRAY);
    reference_gray=cv2.cvtColor(reference,cv2.COLOR_BRT2GRY);
    current_gray=cv2.GuassianBlur(current_gray,(BlurSize,BlurSize),0);
    reference_gray=cv2.GuassianBlur(reference_gray,(BlurSize,BlurSize),0);

    diff=cv2.absdiff(current_gray,reference_gray);
    diff=cv2.bitwise_and(diff,diff,mask=mask);

    _,binary=cv2.threshold(diff,thresholdValue,255,cv2.THRESH_BINARY);

    kernel=np.ones((3,3),np.uint8);
    binary=cv2.morphologyEX(binary,cv2.MORPH_OPEN,kernel);
    binary=cv2.morphologyEX(binary,cv2.MORPH_CLOSE,kernel);

    contours,_=cv2.findcontours(cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);

#create label results of detection
    detectRes=frame.copy();
    ObjectCount=0;
    for contour in contours:
        area=cv2.contourArea(contour);
        if area< StandardMINArea: continue;
        x,y,w,h=cv2.boundingRect(contour);

        if y<8: drawX=x+w;drawY=y+h+8;
        else:drawX=x;drawY=y-8;
        #draw rectangle --show the detect result
        cv2.rectangle(detectRes,(x,y),(x+w,x+h),(0,255,0),2);
        cv2.putText(detectRes,
                    f"Object{area:.of}px",
                    (drawX,drawY),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0,255,0),
                    2
                    )
        ObjectCount+=1;

    status="OBJECTS DETECTED: ALARM" if ObjectCount else "NOTHING DETECTED:OK";

    cv2.putText(detectRes,
                status,
                (10,65),                    #TO DO:NEED ADJUSTMENTS 
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0,255,0),
                2
                )
    cv2.putText(detectRes,
                f"No. of Foreign Objets:{ObjectCount}",
                (10,95),                    #TO DO:NEED ADJUSTMENTS 
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0,255,0),
                2
                )

    return detectRes,binary,ObjectCount; 
#RUN TEST
