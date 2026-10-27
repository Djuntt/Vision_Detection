import argparse
from pathlib import Path
from datetime import datetime

import cv2
import Detection

BASE_DIR = Path(__file__).resolve().parent
REFERENCE_DIR = BASE_DIR / "RefPic"
REFERENCE_IMAGE = REFERENCE_DIR / "Ref1.png"
TEST_DIR = BASE_DIR / "TestPic"
RESULT_DIR = BASE_DIR / "Results"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def read_pictures(folder):
    """Yield readable images one at a time to limit batch memory use."""
    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"Image folder does not exist: {folder}")
    for image_path in sorted(folder.iterdir()):
        if not image_path.is_file() or image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"Warning: Cannot read {image_path}", flush=True)
            continue
        yield image_path, image


def main(show_windows=False):
    reference = cv2.imread(str(REFERENCE_IMAGE))
    if reference is None:
        raise ValueError(f"Cannot read fixed reference image: {REFERENCE_IMAGE}")

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    processed = 0
    for image_path, frame in read_pictures(TEST_DIR):
        print(f"Processing {image_path.name}...", flush=True)
        comparison_reference = reference
        if reference.shape[:2] != frame.shape[:2]:
            comparison_reference = cv2.resize(reference, (frame.shape[1], frame.shape[0]))
        # Generate the ROI at the comparison resolution; preserve the original reference.
        mask, _ = Detection.disk_mask(comparison_reference)
        result, binary, count = Detection.detection(frame, comparison_reference, mask)
        for suffix, image in (("detection", result), ("mask", binary)):
            output_path = RESULT_DIR / f"{image_path.name}_{suffix}.png"
            if not cv2.imwrite(str(output_path), image):
                raise OSError(f"Cannot save detection output: {output_path}")
        processed += 1
        print(f"{image_path.name}: {count} detected region(s); saved to {RESULT_DIR}", flush=True)

        if show_windows:
            try:
                for title, image in (("Foreign Object Detection", result), ("Difference mask", binary)):
                    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
                    cv2.resizeWindow(title, 1000, 750)
                    cv2.imshow(title, image)
                cv2.waitKey(0)
            finally:
                cv2.destroyAllWindows()

    if processed:
        print(f"Finished: {processed} image(s). Results: {RESULT_DIR}", flush=True)
    else:
        print(f"No readable test images found in {TEST_DIR}", flush=True)


def run_camera(args):
    from camera_controller import MindVisionCamera

    reference = cv2.imread(str(REFERENCE_IMAGE))
    if reference is None:
        raise ValueError(f"Cannot read fixed reference image: {REFERENCE_IMAGE}")
    mask, _ = Detection.disk_mask(reference)
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    alarm_latched = False
    positive_frames = 0
    print("Monitoring: Ctrl+C to stop; Q to quit preview. Software alarm stays latched until restart.", flush=True)
    try:
        with MindVisionCamera(args.camera_index, args.sdk_dir, args.exposure_us,
                              args.flip_vertical, frame_rate=args.frame_rate,
                              light_frequency=args.light_frequency) as camera:
            while True:
                frame = camera.read()
                if frame.shape != reference.shape:
                    raise ValueError(
                        f"Camera shape {frame.shape} differs from reference {reference.shape}. "
                        "Capture a clean reference using identical camera settings and orientation."
                    )
                result, binary, count = Detection.detection(frame, reference, mask)
                positive_frames = positive_frames + 1 if count else 0
                if not alarm_latched and positive_frames >= args.confirm_frames:
                    alarm_latched = True
                    print("FOREIGN OBJECT ALARM (software only; no physical output connected)", flush=True)
                    event = datetime.now().strftime("alarm_%Y%m%d_%H%M%S_%f")
                    outputs = (
                        (TEST_DIR / f"{event}_raw.png", frame),
                        (RESULT_DIR / f"{event}_detection.png", result),
                        (RESULT_DIR / f"{event}_mask.png", binary),
                    )
                    for path, image in outputs:
                        if not cv2.imwrite(str(path), image):
                            raise OSError(f"Cannot save alarm evidence: {path}")
                    print(f"Raw capture saved in {TEST_DIR}; results saved in {RESULT_DIR}", flush=True)
                if args.show:
                    cv2.namedWindow("Camera inspection", cv2.WINDOW_NORMAL)
                    cv2.resizeWindow("Camera inspection", 1000, 750)
                    cv2.imshow("Camera inspection", result)
                    if cv2.waitKey(1) & 0xFF in (ord('q'), 27):
                        break
    except KeyboardInterrupt:
        print("Camera monitoring stopped.", flush=True)
    except Exception:
        print("VISION FAULT: inspection unavailable; this is not a clear result.", flush=True)
        raise
    finally:
        if args.show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare TestPic images with RefPic/Ref1.png.")
    parser.add_argument("--show", action="store_true", help="Preview each saved result; press a key to advance.")
    parser.add_argument("--camera", action="store_true", help="Monitor using the Windows MindVision SDK")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--sdk-dir", help="Native SDK DLL directory")
    parser.add_argument("--exposure-us", type=float, default=10000, help="Legacy option; ignored while automatic exposure is enabled")
    parser.add_argument("--frame-rate", type=int, default=10, help="Target capture rate in fps (default: 10)")
    parser.add_argument("--light-frequency", type=int, choices=(50, 60), default=50, help="Anti-flicker mains frequency in Hz")
    parser.add_argument("--flip-vertical", action="store_true", help="Flip frames to match reference orientation")
    parser.add_argument("--confirm-frames", type=int, default=3)
    args = parser.parse_args()
    if args.confirm_frames < 1:
        parser.error("--confirm-frames must be at least 1")
    if args.camera:
        run_camera(args)
    else:
        main(show_windows=args.show)
