# Vision_Detection

Version1 use known picture as reference and test picture to try the result

Run `python main.py` to compare all supported images directly inside `TestPic/`
against the fixed reference `RefPic/Ref1.png`. Paths are relative to `main.py`,
so the project can be moved or launched from another working directory.

The program creates `Results/` automatically and saves an annotated image and
a binary difference mask for each input, for example `Test1.png_detection.png`
and `Test1.png_mask.png`. Running again overwrites outputs with the same names.
By default, all images are processed without opening windows or waiting for keys.
Use `python main.py --show` to preview results, pressing a key to advance.

For processing without display windows, call `main.main(show_windows=False)`.

Detection compensates for global exposure differences using a robust brightness
gain/offset fit, then smooths noise and joins nearby changed pixels. It assumes
the camera is stationary and most of the circular inspection area is unchanged.
Saved masks contain accepted object regions after minimum-area filtering;
enclosed holes are filled. These masks are approximate change regions, not exact
object outlines. Camera movement and local shadows can still cause false alarms.

## Windows MindVision camera

Install the MindVision Windows SDK and camera driver. Confirm acquisition in
the vendor application, then close it before running Python. Python and the
native SDK must have matching architecture (normally both 64-bit).

Run live inspection:

```powershell
python main.py --camera --show
```

If the native library cannot be found, supply its directory:

```powershell
python main.py --camera --show --sdk-dir "C:\path\to\SDK\x64"
```

The directory must contain `MVCAMSDK_X64.dll` for 64-bit Python, or
`MVCAMSDK.dll` for 32-bit Python, with its required dependencies installed.
No SDK is needed for the existing `python main.py` folder mode.

Camera mode enables automatic exposure and anti-flicker at 50 Hz, and requests
10 fps. Change these with `--light-frequency 60` or `--frame-rate 10`.
`--exposure-us` is retained for command compatibility but ignored during AE.
Select a device with `--camera-index 0`. If direct frame-rate control is not
supported, paced software triggers limit capture to at most the requested rate.
Exposure, transfer time and processing can reduce the achieved rate; 10 fps
capture does not guarantee 10 inspections per second.
Other camera settings come from the SDK's loaded configuration. Capture the
clean `RefPic/Ref1.png` reference with the same settings, lighting, position,
resolution and orientation. Camera mode rejects mismatched resolutions.
If the displayed SDK image is upside down, use `--flip-vertical` consistently
with the reference orientation.

After three consecutive positive frames (`--confirm-frames 3`), a software alarm
latches until the application restarts. Evidence is saved once per alarm as
lossless PNG files with a matching timestamp:

- `TestPic/alarm_<timestamp>_raw.png`: captured camera image.
- `Results/alarm_<timestamp>_detection.png`: annotated detection result.
- `Results/alarm_<timestamp>_mask.png`: accepted object mask.

Both folders are created automatically if needed. Frames without a confirmed
alarm are processed in memory and are not saved.
This is a console alarm only: PLC communication, physical outputs, operator
reset and an external watchdog remain to be implemented. Processing speed
determines confirmation latency; this is not a fixed-duration confirmation.
Camera/processing failures stop monitoring and report a vision fault.
Press Q/Esc in preview or Ctrl+C in the terminal to stop.
