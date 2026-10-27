import cv2
import numpy as np
import os

#Configuration-----------------------------------------------------------------------------
cameraIndex=0; #Support maximum of 2 according to MindVision 
initialPicture="Ref1.png"; #Reference Picture

#To be Manually Set 
CENTER_X=None;
CENTER_Y=None;
RADIUS=None; 

#Comparison Parameter
BlurSize=15;
thresholdValue=25;
StandardMINArea=1000; #comparion area; adjust to improve accuracy
#------------------------------------------------------------------------------------------
#Disk Mask 
def disk_mask(image): 
    height, width =image.shape[:2];
    center_x= CENTER_X if CENTER_X is not None else width//2;
    center_y= CENTER_Y if CENTER_Y is not None else height//2;
    radius= RADIUS if RADIUS is not None else int(
        min(height,width)*0.45
    )

    mask=np.zeros((height,width),dtype=np.uint8);
    cv2.circle(mask,(int(center_x),int(center_y)),int(radius),255,-1);

    return mask, (int(center_x),int(center_y),int(radius));

def normalize_reference(current_gray, reference_gray, mask):
    """Robustly fit frame = gain * reference + offset inside the inspection ROI.

    Trim outliers so added objects do not drive the exposure correction.
    This assumes most of the inspection area is unchanged and aligned.
    """
    reference_values = reference_gray[mask != 0][::16].astype(np.float32)
    current_values = current_gray[mask != 0][::16].astype(np.float32)
    if reference_values.size < 20:
        raise ValueError("Inspection mask must contain at least 320 pixels")
    keep = np.ones(reference_values.size, dtype=bool)
    gain, offset = 1.0, float(np.median(current_values - reference_values))
    for _ in range(5):
        if np.std(reference_values[keep]) < 1:
            # Uniform references cannot independently determine gain and offset.
            break
        design = np.column_stack((reference_values[keep], np.ones(np.count_nonzero(keep))))
        gain, offset = np.linalg.lstsq(design, current_values[keep], rcond=None)[0]
        residual = current_values - (gain * reference_values + offset)
        center = np.median(residual)
        tolerance = max(5.0, 3 * 1.4826 * np.median(np.abs(residual - center)))
        keep = np.abs(residual - center) < tolerance
        if np.count_nonzero(keep) < 20:
            raise ValueError("Not enough unchanged pixels for exposure correction")
    return np.clip(gain * reference_gray.astype(np.float32) + offset, 0, 255)


#Comparison
def detection(frame,reference, mask):
    for name, image in (("frame", frame), ("reference", reference)):
        if not isinstance(image, np.ndarray) or image.size == 0:
            raise ValueError(f"{name} must be a non-empty BGR image")
        if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
            raise ValueError(f"{name} must be a uint8 BGR image with 3 channels")
    if frame.shape[:2] != reference.shape[:2]:
        raise ValueError("frame and reference must have matching height and width")
    if (not isinstance(mask, np.ndarray) or mask.dtype != np.uint8
            or mask.shape != frame.shape[:2]):
        raise ValueError("mask must be a uint8 array matching the frame height and width")

    current_gray= cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY);
    reference_gray=cv2.cvtColor(reference,cv2.COLOR_BGR2GRAY);
    current_gray=cv2.GaussianBlur(current_gray,(BlurSize,BlurSize),0);
    reference_gray=cv2.GaussianBlur(reference_gray,(BlurSize,BlurSize),0);

    compensated_reference = normalize_reference(current_gray, reference_gray, mask)
    diff = np.abs(current_gray.astype(np.float32) - compensated_reference).astype(np.uint8)
    diff=cv2.bitwise_and(diff,diff,mask=mask);

    _,binary=cv2.threshold(diff,thresholdValue,255,cv2.THRESH_BINARY);

    # Scale cleanup to the image resolution (the samples are about 20 MP).
    cleanup_size = max(3, int(round(min(frame.shape[:2]) / 300)) | 1)
    kernel=np.ones((cleanup_size,cleanup_size),np.uint8);
    binary=cv2.morphologyEx(binary,cv2.MORPH_OPEN,kernel);
    close_kernel = np.ones((cleanup_size * 2 - 1, cleanup_size * 2 - 1), np.uint8)
    binary=cv2.morphologyEx(binary,cv2.MORPH_CLOSE,close_kernel);
    binary = cv2.bitwise_and(binary, mask)

    contours,_=cv2.findContours(binary,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);

#create label results of detection
    detectRes=frame.copy();
    accepted_mask = np.zeros_like(binary)
    text_scale = max(0.6, frame.shape[1] / 1800)
    text_thickness = max(1, round(text_scale))
    ObjectCount=0;
    for contour in contours:
        area=cv2.contourArea(contour);
        if area<StandardMINArea: continue;
        cv2.drawContours(accepted_mask, [contour], -1, 255, cv2.FILLED)
        x,y,w,h=cv2.boundingRect(contour);

        if y<8: drawX=x+w;drawY=y+h+8;
        else:drawX=x;drawY=y-8;
        #draw rectangle --show the detect result
        cv2.rectangle(detectRes,(x,y),(x+w,y+h),(0,255,0),max(2, text_thickness * 2));
        cv2.putText(detectRes,
                    f"Object{area:.0f}px",
                    (drawX,drawY),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    text_scale,
                    (0,255,0),
                    text_thickness
                    )
        ObjectCount+=1;

    status="OBJECTS DETECTED: ALARM" if ObjectCount else "NOTHING DETECTED:OK";

    cv2.putText(detectRes,
                status,
                (20, int(35 * text_scale)),
                cv2.FONT_HERSHEY_SIMPLEX,
                text_scale,
                (0,0,255),
                text_thickness
                )
    cv2.putText(detectRes,
                f"Foreign objects: {ObjectCount}",
                (20, int(75 * text_scale)),
                cv2.FONT_HERSHEY_SIMPLEX,
                text_scale,
                (0,0,255),
                text_thickness
                )



    #create digital io to triger alarm
    

    return detectRes,accepted_mask,ObjectCount;
#RUN TEST
