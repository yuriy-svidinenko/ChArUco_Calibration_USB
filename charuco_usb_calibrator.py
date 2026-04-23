#!/usr/bin/env python
"""
InvivoCloud Inc. ChArUco USB camera calibration helper for Briareus or RRS cameras. V1.03

Use Allentown cage as the reference - 7.1 in x 15 in appx

DICT 7x5 boards, 25 samples

See arguments below!

RES: 1280x720 by default

Examples:
  python charuco_usb_calibrator.py generate-board --output charuco_board.png
  python charuco_usb_calibrator.py capture --camera 0 --output calibration.json
  python charuco_usb_calibrator.py calibrate-images --images samples/*.png --output calibration.json

Install dependency:
  python -m pip install opencv-contrib-python numpy
"""

import argparse
import glob
import json
import os
import sys
import time
from datetime import datetime


cv2 = None
np = None


ARUCO_DICTS = {
    "4x4_50": "DICT_4X4_50",
    "4x4_100": "DICT_4X4_100",
    "5x5_100": "DICT_5X5_100",
    "5x5_250": "DICT_5X5_250",
    "6x6_250": "DICT_6X6_250",
    "6x6_1000": "DICT_6X6_1000",
}

def require_aruco():
    require_opencv()
    if not hasattr(cv2, "aruco"):
        print("This script requires OpenCV with the aruco module.")
        print("Install with: python -m pip install opencv-contrib-python numpy")
        sys.exit(1)
    if not hasattr(cv2.aruco, "calibrateCameraCharuco"):
        print("Your OpenCV build does not include ChArUco calibration.")
        print("Install/upgrade with: python -m pip install --upgrade opencv-contrib-python numpy")
        sys.exit(1)


def require_opencv():
    global cv2, np
    if cv2 is not None:
        return
    try:
        import cv2 as cv2_module
        import numpy as np_module
    except ImportError as exc:
        print("Missing dependency:", exc)
        print("Install with: python -m pip install opencv-contrib-python numpy")
        sys.exit(1)
    cv2 = cv2_module
    np = np_module


def make_dictionary(name):
    require_aruco()
    try:
        dict_id = getattr(cv2.aruco, ARUCO_DICTS[name])
    except KeyError:
        choices = ", ".join(sorted(ARUCO_DICTS))
        raise SystemExit(f"Unknown dictionary '{name}'. Choices: {choices}")
    return cv2.aruco.getPredefinedDictionary(dict_id)


def make_board(squares_x, squares_y, square_length, marker_length, dictionary):
    require_aruco()
    if hasattr(cv2.aruco, "CharucoBoard_create"):
        return cv2.aruco.CharucoBoard_create(
            squares_x,
            squares_y,
            square_length,
            marker_length,
            dictionary,
        )
    return cv2.aruco.CharucoBoard(
        (squares_x, squares_y),
        square_length,
        marker_length,
        dictionary,
    )


def draw_board(board, image_size, margin, border_bits):
    if hasattr(board, "generateImage"):
        return board.generateImage(image_size, marginSize=margin, borderBits=border_bits)
    return board.draw(image_size, marginSize=margin, borderBits=border_bits)


def detector_parameters():
    if hasattr(cv2.aruco, "DetectorParameters"):
        return cv2.aruco.DetectorParameters()
    return cv2.aruco.DetectorParameters_create()


def detect_markers(gray, dictionary, parameters):
    if hasattr(cv2.aruco, "ArucoDetector"):
        detector = cv2.aruco.ArucoDetector(dictionary, parameters)
        return detector.detectMarkers(gray)
    return cv2.aruco.detectMarkers(gray, dictionary, parameters=parameters)


def detect_charuco(gray, board, dictionary, parameters, min_corners):
    marker_corners, marker_ids, rejected = detect_markers(gray, dictionary, parameters)
    if marker_ids is None or len(marker_ids) == 0:
        return None, None, marker_corners, marker_ids, rejected, 0

    try:
        cv2.aruco.refineDetectedMarkers(gray, board, marker_corners, marker_ids, rejected)
    except cv2.error:
        pass

    count, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
        marker_corners,
        marker_ids,
        gray,
        board,
    )
    if charuco_ids is None or charuco_corners is None or count < min_corners:
        return None, None, marker_corners, marker_ids, rejected, int(count or 0)
    return charuco_corners, charuco_ids, marker_corners, marker_ids, rejected, int(count)


def write_calibration(output_path, data):
    serializable = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "opencv_version": cv2.__version__,
        **data,
        "camera_matrix": data["camera_matrix"].tolist(),
        "distortion_coefficients": data["distortion_coefficients"].tolist(),
    }
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(serializable, file, indent=2)
        file.write("\n")


def calibrate(samples_corners, samples_ids, image_size, board):
    if len(samples_corners) < 5:
        raise RuntimeError("Need at least 5 accepted ChArUco samples; 15-30 is better.")
    rms, camera_matrix, distortion, rvecs, tvecs = cv2.aruco.calibrateCameraCharuco(
        charucoCorners=samples_corners,
        charucoIds=samples_ids,
        board=board,
        imageSize=image_size,
        cameraMatrix=None,
        distCoeffs=None,
    )
    return rms, camera_matrix, distortion, rvecs, tvecs


def open_camera(index, width, height):
    backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
    cap = cv2.VideoCapture(index, backend)
    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera index {index}.")
    return cap


def command_generate_board(args):
    dictionary = make_dictionary(args.dictionary)
    board = make_board(
        args.squares_x,
        args.squares_y,
        args.square_length,
        args.marker_length,
        dictionary,
    )
    image = draw_board(board, (args.pixels_w, args.pixels_h), args.margin, args.border_bits)
    if not cv2.imwrite(args.output, image):
        raise RuntimeError(f"Could not write board image to {args.output}")
    print(f"Wrote {args.output}")
    print(
        "Print it flat. Keep these physical settings for capture/calibration: "
        f"{args.squares_x}x{args.squares_y}, square={args.square_length}, "
        f"marker={args.marker_length}, dictionary={args.dictionary}"
    )


def command_capture(args):
    dictionary = make_dictionary(args.dictionary)
    board = make_board(
        args.squares_x,
        args.squares_y,
        args.square_length,
        args.marker_length,
        dictionary,
    )
    parameters = detector_parameters()
    cap = open_camera(args.camera, args.width, args.height)
    samples_corners = []
    samples_ids = []
    image_size = None
    last_auto_capture = 0.0

    if args.save_frames:
        os.makedirs(args.save_frames, exist_ok=True)

    print("Aruco/Charuco USB calibration, v1.4, InvivoCloud Inc.")
    print("Controls: Space/C = capture sample, A = toggle auto-capture, Q/Esc = finish")
    print("Move the board around: center, corners, tilted, near, and far.")
    auto_capture = args.auto

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError("Camera frame read failed.")
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            image_size = (gray.shape[1], gray.shape[0])
            corners, ids, marker_corners, marker_ids, _rejected, count = detect_charuco(
                gray,
                board,
                dictionary,
                parameters,
                args.min_corners,
            )

            preview = frame.copy()
            if marker_ids is not None and len(marker_ids):
                cv2.aruco.drawDetectedMarkers(preview, marker_corners, marker_ids)
            if corners is not None:
                cv2.aruco.drawDetectedCornersCharuco(preview, corners, ids)

            status = (
                f"samples={len(samples_corners)}/{args.samples} "
                f"corners={count} auto={'on' if auto_capture else 'off'}"
            )
            color = (0, 220, 0) if corners is not None else (0, 180, 255)
            cv2.putText(preview, status, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(
                preview,
                "Space/C capture  A auto  Q finish",
                (20, preview.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )
            cv2.imshow("ChArUco USB Camera Calibration", preview)

            key = cv2.waitKey(1) & 0xFF
            should_capture = key in (ord(" "), ord("c"), ord("C"))
            if key in (ord("a"), ord("A")):
                auto_capture = not auto_capture
            if auto_capture and corners is not None:
                now = time.time()
                should_capture = should_capture or (now - last_auto_capture >= args.auto_interval)
            if key in (ord("q"), ord("Q"), 27):
                break

            if should_capture and corners is not None:
                samples_corners.append(corners)
                samples_ids.append(ids)
                last_auto_capture = time.time()
                print(f"Accepted sample {len(samples_corners)} with {count} corners")
                if args.save_frames:
                    frame_path = os.path.join(args.save_frames, f"sample_{len(samples_corners):03d}.png")
                    cv2.imwrite(frame_path, frame)
                if len(samples_corners) >= args.samples:
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    rms, camera_matrix, distortion, _rvecs, _tvecs = calibrate(
        samples_corners,
        samples_ids,
        image_size,
        board,
    )
    write_calibration(
        args.output,
        {
            "rms_reprojection_error": float(rms),
            "image_size": list(image_size),
            "samples": len(samples_corners),
            "board": board_metadata(args),
            "camera_matrix": camera_matrix,
            "distortion_coefficients": distortion,
        },
    )
    print(f"Wrote {args.output}")
    print(f"RMS reprojection error: {rms:.4f}")


def command_calibrate_images(args):
    dictionary = make_dictionary(args.dictionary)
    board = make_board(
        args.squares_x,
        args.squares_y,
        args.square_length,
        args.marker_length,
        dictionary,
    )
    parameters = detector_parameters()
    image_paths = expand_image_args(args.images)
    if not image_paths:
        raise RuntimeError("No images matched.")

    samples_corners = []
    samples_ids = []
    image_size = None

    for path in image_paths:
        image = cv2.imread(path, cv2.IMREAD_COLOR)
        if image is None:
            print(f"Skipping unreadable image: {path}")
            continue
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        size = (gray.shape[1], gray.shape[0])
        if image_size is None:
            image_size = size
        elif image_size != size:
            print(f"Skipping different-sized image: {path}")
            continue

        corners, ids, _marker_corners, _marker_ids, _rejected, count = detect_charuco(
            gray,
            board,
            dictionary,
            parameters,
            args.min_corners,
        )
        if corners is None:
            print(f"Rejected {path}: only {count} ChArUco corners")
            continue
        samples_corners.append(corners)
        samples_ids.append(ids)
        print(f"Accepted {path}: {count} corners")

    rms, camera_matrix, distortion, _rvecs, _tvecs = calibrate(
        samples_corners,
        samples_ids,
        image_size,
        board,
    )
    write_calibration(
        args.output,
        {
            "rms_reprojection_error": float(rms),
            "image_size": list(image_size),
            "samples": len(samples_corners),
            "board": board_metadata(args),
            "camera_matrix": camera_matrix,
            "distortion_coefficients": distortion,
        },
    )
    print(f"Wrote {args.output}")
    print(f"RMS reprojection error: {rms:.4f}")


def board_metadata(args):
    return {
        "squares_x": args.squares_x,
        "squares_y": args.squares_y,
        "square_length": args.square_length,
        "marker_length": args.marker_length,
        "dictionary": args.dictionary,
    }


def expand_image_args(patterns):
    paths = []
    for pattern in patterns:
        matches = glob.glob(pattern)
        paths.extend(matches if matches else [pattern])
    return sorted(dict.fromkeys(paths))


def add_board_args(parser):
    parser.add_argument("--squares-x", type=int, default=7, help="Number of chessboard squares across.")
    parser.add_argument("--squares-y", type=int, default=5, help="Number of chessboard squares down.")
    parser.add_argument("--square-length", type=float, default=0.035, help="Printed square size in meters.")
    parser.add_argument("--marker-length", type=float, default=0.026, help="Printed marker size in meters.")
    parser.add_argument("--dictionary", default="5x5_100", choices=sorted(ARUCO_DICTS))


def build_parser():
    parser = argparse.ArgumentParser(description="Generate and use a ChArUco board for USB camera calibration.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen = subparsers.add_parser("generate-board", help="Create a printable ChArUco board image.")
    add_board_args(gen)
    gen.add_argument("--output", default="charuco_board.png")
    gen.add_argument("--pixels-w", type=int, default=2200)
    gen.add_argument("--pixels-h", type=int, default=1600)
    gen.add_argument("--margin", type=int, default=80)
    gen.add_argument("--border-bits", type=int, default=1)
    gen.set_defaults(func=command_generate_board)

    capture = subparsers.add_parser("capture", help="Capture samples from a USB camera and calibrate.")
    add_board_args(capture)
    capture.add_argument("--camera", type=int, default=0)
    capture.add_argument("--width", type=int, default=1280)
    capture.add_argument("--height", type=int, default=720)
    capture.add_argument("--samples", type=int, default=25)
    capture.add_argument("--min-corners", type=int, default=8)
    capture.add_argument("--output", default="camera_calibration.json")
    capture.add_argument("--save-frames", default=None, help="Optional directory for accepted calibration frames.")
    capture.add_argument("--auto", action="store_true", help="Automatically capture when enough corners are visible.")
    capture.add_argument("--auto-interval", type=float, default=1.0, help="Seconds between auto-captured samples.")
    capture.set_defaults(func=command_capture)

    cal = subparsers.add_parser("calibrate-images", help="Calibrate from saved ChArUco board images.")
    add_board_args(cal)
    cal.add_argument("--images", nargs="+", required=True)
    cal.add_argument("--samples", type=int, default=25, help=argparse.SUPPRESS)
    cal.add_argument("--min-corners", type=int, default=8)
    cal.add_argument("--output", default="camera_calibration.json")
    cal.set_defaults(func=command_calibrate_images)

    return parser


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
