import Detection 
import cv2
import numpy as np
import os
import Detection 

initialPicture="/Users/daijun/Desktop/CODE/Vision_Detection/Ref.png"; #Reference Picture

def main():
    #TO DO: Camera Controller


    #NOW : TEST USING KNOWN PICTURES
    reference=None;
    if os.path.exists(initialPicture):
        reference=cv2.imread(initialPicture);
        
        mask,cicle = Detection.disk_mask(reference);
        x,y,radius= cicle;

    while True: 
        #TO DO : READ DATA FROM CAMERA 
        #check read results : if not break;


        #A test fram given
        frame1="/Users/daijun/Desktop/CODE/Vision_Detection/Test.png";
        frame=cv2.imread(frame1);
        if reference is not None:
            if reference.shape!=frame.shape:
                reference =cv2.resize(reference,(frame.shape[1],frame.shape[0])
                                      )
            result,binary,count=Detection.detection(
                frame,reference,mask
            )

            cv2.imshow("Foreign Object Detection:", result);
            cv2.imshow("Difference mask:", binary);
            cv2.waitKey(0);
            cv2.destroyAllWindows();
        #TO DO : if ref =None, user need to set it manually    
        #else: 
        break   
            

if __name__=="__main__":
    main()