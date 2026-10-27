"""MindVision Windows acquisition; folder mode does not require the native SDK."""
import ctypes
import importlib
import os
import platform
import time
from pathlib import Path

import cv2
import numpy as np


class MindVisionCamera:
    def __init__(self, index=0, sdk_dir=None, exposure_us=10000, flip_vertical=False,
                 frame_rate=10, light_frequency=50):
        self.index, self.sdk_dir = index, sdk_dir
        self.exposure_us, self.flip_vertical = exposure_us, flip_vertical
        self.sdk = self.handle = self.buffer = self.dll_directory = None
        self.frame_rate, self.light_frequency = frame_rate, light_frequency
        self.software_trigger = False
        self.next_capture = 0.0

    def _check(self, status):
        if status != self.sdk.CAMERA_STATUS_SUCCESS:
            raise self.sdk.CameraException(status)

    def __enter__(self):
        if platform.system() != "Windows":
            raise RuntimeError("This adapter requires the MindVision SDK for Windows")
        if self.index < 0 or self.exposure_us <= 0:
            raise ValueError("Camera index must be nonnegative and exposure must be positive")
        if self.frame_rate < 1 or int(self.frame_rate) != self.frame_rate:
            raise ValueError("Frame rate must be a positive integer")
        if self.light_frequency not in (50, 60):
            raise ValueError("Light frequency must be 50 or 60 Hz")
        try:
            if self.sdk_dir:
                self.dll_directory = os.add_dll_directory(str(Path(self.sdk_dir).resolve()))
            try:
                self.sdk = importlib.import_module("mvsdk")
            except OSError as error:
                raise RuntimeError(
                    "Cannot load MindVision SDK. Install Windows SDK/drivers, match Python "
                    "and DLL bitness, and specify --sdk-dir if needed. " + str(error)
                ) from error
            devices = self.sdk.CameraEnumerateDevice()
            self._check(self.sdk.GetLastError())
            if self.index >= len(devices):
                raise RuntimeError(f"Camera index {self.index} unavailable; found {len(devices)} camera(s)")
            self.handle = self.sdk.CameraInit(devices[self.index], -1, -1)
            capability = self.sdk.CameraGetCapability(self.handle)
            self._check(self.sdk.GetLastError())
            self.channels = 1 if capability.sIspCapacity.bMonoSensor else 3
            fmt = self.sdk.CAMERA_MEDIA_TYPE_MONO8 if self.channels == 1 else self.sdk.CAMERA_MEDIA_TYPE_BGR8
            self._check(self.sdk.CameraSetIspOutFormat(self.handle, fmt))
            self._check(self.sdk.CameraSetTriggerMode(self.handle, 0))
            self._check(self.sdk.CameraSetAeState(self.handle, 1))
            self._check(self.sdk.CameraSetAntiFlick(self.handle, 1))
            self._check(self.sdk.CameraSetLightFrequency(self.handle, 0 if self.light_frequency == 50 else 1))
            # AE owns exposure; do not issue a conflicting manual exposure command.
            try:
                rate_status = self.sdk.CameraSetFrameRate(self.handle, self.frame_rate)
            except AttributeError:
                rate_status = self.sdk.CAMERA_STATUS_NOT_SUPPORTED
            if rate_status == self.sdk.CAMERA_STATUS_NOT_SUPPORTED:
                self._check(self.sdk.CameraSetTriggerMode(self.handle, 1))
                self.software_trigger = True
                print(f"Camera rate control unsupported; using software triggers at up to {self.frame_rate} fps.", flush=True)
            else:
                self._check(rate_status)
            self.capacity = capability.sResolutionRange.iWidthMax * capability.sResolutionRange.iHeightMax * self.channels
            self.buffer = self.sdk.CameraAlignMalloc(self.capacity, 16)
            if not self.buffer:
                raise MemoryError("Cannot allocate camera image buffer")
            self._check(self.sdk.CameraPlay(self.handle))
            print(f"Auto exposure ON; anti-flicker ON ({self.light_frequency} Hz); target {self.frame_rate} fps.", flush=True)
            return self
        except BaseException:
            self.close()
            raise

    def read(self, timeout_ms=2000):
        if self.handle is None:
            raise RuntimeError("Camera is not open")
        if self.software_trigger:
            delay = self.next_capture - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            self._check(self.sdk.CameraSoftTrigger(self.handle))
            self.next_capture = time.monotonic() + 1.0 / self.frame_rate
        raw, head = self.sdk.CameraGetImageBuffer(self.handle, timeout_ms)
        try:
            self._check(self.sdk.CameraImageProcess(self.handle, raw, self.buffer, head))
        finally:
            self._check(self.sdk.CameraReleaseImageBuffer(self.handle, raw))
        if self.flip_vertical:
            self._check(self.sdk.CameraFlipFrameBuffer(self.buffer, head, 1))
        size = head.iWidth * head.iHeight * self.channels
        if size <= 0 or size > self.capacity or head.uBytes != size:
            raise RuntimeError("Unexpected camera image dimensions or pixel layout")
        data = (ctypes.c_ubyte * size).from_address(self.buffer)
        frame = np.ctypeslib.as_array(data).reshape(head.iHeight, head.iWidth, self.channels).copy()
        return cv2.cvtColor(frame[:, :, 0], cv2.COLOR_GRAY2BGR) if self.channels == 1 else frame

    def close(self):
        try:
            if self.handle is not None:
                self.sdk.CameraUnInit(self.handle)
        finally:
            self.handle = None
            try:
                if self.buffer:
                    self.sdk.CameraAlignFree(self.buffer)
            finally:
                self.buffer = None
                if self.dll_directory is not None:
                    self.dll_directory.close()
                    self.dll_directory = None

    def __exit__(self, *args):
        self.close()
