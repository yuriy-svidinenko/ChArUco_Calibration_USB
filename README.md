# InvivoCloud Inc. ChArUco USB Camera Calibrator, v 1.4

Python helper for calibrating a Briareus or RRS USB high FOV camera with a ChArUco board.

The script supports three workflows:

- generate a printable ChArUco board image (or use Allentown cage board)
- preview a live USB camera feed and capture calibration samples
- calibrate from previously saved board images

The main script is [charuco_usb_calibrator.py](C:/Users/tinra/Documents/Playground/charuco_usb_calibrator.py).

## Files

- [charuco_usb_calibrator.py] - CLI tool
- [requirements-charuco.txt] - Python dependencies
- [AT_Cage_charuco.png] - Sample Allentown cage board

## Requirements

- Python 3.9+
- `opencv-contrib-python`
- `numpy`
- A webcam or USB camera for live capture
- A printed ChArUco board

Install dependencies:

```powershell
python -m pip install -r requirements-charuco.txt
```

If OpenCV is missing, the script exits with an install hint.

## Default Board Settings

These are the current script defaults:

- `--squares-x 7`
- `--squares-y 5`
- `--square-length 0.035`
- `--marker-length 0.026`
- `--dictionary 5x5_100`

If your printed board uses different dimensions or a different ArUco dictionary, pass the correct values on the command line.

## 1. Generate a Board

Create a printable board image:

```powershell
python charuco_usb_calibrator.py generate-board --output charuco_board.png
```

Example with explicit board settings:

```powershell
python charuco_usb_calibrator.py generate-board `
  --squares-x 7 `
  --squares-y 5 `
  --square-length 0.035 `
  --marker-length 0.026 `
  --dictionary 5x5_100 `
  --output charuco_board.png
```

## 2. Live Camera Preview and Calibration

Start live preview from USB camera index `0`:

```powershell
python charuco_usb_calibrator.py capture --camera 0 --output camera_calibration.json
```

Example with automatic sample capture and saved frames:

```powershell
python charuco_usb_calibrator.py capture `
  --camera 0 `
  --width 1280 `
  --height 720 `
  --samples 25 `
  --auto `
  --save-frames samples `
  --output camera_calibration.json
```

### Preview Controls

- `Space` or `C` - capture current sample
- `A` - toggle automatic capture
- `Q` or `Esc` - finish capture

### Capture Tips

- Move the board across the center and all four corners.
- Tilt the board at different angles.
- Capture near and far distances.
- Avoid blurry frames.
- A wider spread of poses usually gives better calibration.
- The script requires at least 5 accepted ChArUco samples, but 15 to 30 is better.

The preview overlay shows:

- number of accepted samples
- target sample count
- detected ChArUco corner count
- whether auto capture is enabled

## 3. Calibrate from Saved Images

If you already have captured images, calibrate without using the live camera:

```powershell
python charuco_usb_calibrator.py calibrate-images --images samples/*.png --output camera_calibration.json
```

Example with explicit board parameters:

```powershell
python charuco_usb_calibrator.py calibrate-images `
  --images samples/*.png `
  --squares-x 7 `
  --squares-y 5 `
  --square-length 0.035 `
  --marker-length 0.026 `
  --dictionary 5x5_100 `
  --output camera_calibration.json
```

## Output

The calibration result is written to JSON. Example fields:

- `created_at`
- `opencv_version`
- `rms_reprojection_error`
- `image_size`
- `samples`
- `board`
- `camera_matrix`
- `distortion_coefficients`

This JSON can be loaded later by your own camera pipeline or downstream tooling.

## Command Reference

Show general help:

```powershell
python charuco_usb_calibrator.py --help
```

Show capture help:

```powershell
python charuco_usb_calibrator.py capture --help
```

## Troubleshooting

### `No module named 'cv2'`

Install the dependencies:

```powershell
python -m pip install -r requirements-charuco.txt
```

### Board is visible but no corners are accepted

Check:

- square count matches your printed board
- dictionary matches your printed board
- board is well lit
- frame is sharp
- enough of the board is visible

You can also lower the threshold slightly:

```powershell
python charuco_usb_calibrator.py capture --min-corners 6
```

### Camera does not open

Try another camera index:

```powershell
python charuco_usb_calibrator.py capture --camera 1
```

### Calibration quality looks poor

Capture more samples and vary the board position and angle more aggressively. Calibration usually degrades if every image is taken from nearly the same pose.
