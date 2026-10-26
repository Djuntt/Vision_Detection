import Detection 
import cv2
import numpy as np
import os
import Detection 
from pathlib import Path

initialPicture="D:\Code\Vision_Detection-main\RefPic\Ref1.png"; #Reference Picture


BASE_DIR = Path(__file__).resolve().parent
REFERENCE_DIR = BASE_DIR / "RefPic"
TEST_DIR = BASE_DIR / "TestPic"

REFERENCE_IMAGE = REFERENCE_DIR / "Ref1.png"

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"
}


def read_pictures(folder):
    """
    Read all supported image files in a folder.

    Returns a list of (image_path, image) pairs.
    Unreadable images are skipped with a warning.
    """
    folder = Path(folder)

    if not folder.is_dir():
        raise FileNotFoundError(
            f"Image folder does not exist: {folder}"
        )

    pictures = []

    for image_path in sorted(folder.iterdir()):
        if not image_path.is_file():
            continue

        if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        image = cv2.imread(str(image_path))

        if image is None:
            print(f"Warning: Cannot read {image_path.name}")
            continue

        pictures.append((image_path, image))

    return pictures


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
        frame1="D:\Code\Vision_Detection-main\TestPic\Test1.png";
        frame=cv2.imread(frame1);
        if reference is not None:
            if reference.shape!=frame.shape:
                reference =cv2.resize(reference,(frame.shape[1],frame.shape[0])
                                      )
            result,binary,count=Detection.detection(
                frame,reference,mask
            )
            cv2.namedWindow("Foreign Object Detection", cv2.WINDOW_NORMAL);
            cv2.resizeWindow("Foreign Object Detection", x*2, y*2);

            cv2.namedWindow("Difference mask", cv2.WINDOW_NORMAL);
            cv2.resizeWindow("Difference mask", x*2, y*2);

            cv2.imshow("Foreign Object Detection", result);
            cv2.imshow("Difference mask", binary);
            cv2.waitKey(0);
            cv2.destroyAllWindows();
        #TO DO : if ref =None, user need to set it manually    
        #else: 
        break   
            

if __name__=="__main__":
    main()  
