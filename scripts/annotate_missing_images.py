from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
NORMALIZED_SIZE = 1000


def list_image_files(directory: str | Path) -> list[Path]:
    directory = Path(directory)
    return sorted(
        [path for path in directory.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS],
        key=lambda p: p.name.lower(),
    )


def list_json_files(directory: str | Path) -> list[Path]:
    directory = Path(directory)
    return sorted(
        [path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".json"],
        key=lambda p: p.name.lower(),
    )


def find_missing_images(images: Iterable[Path], json_files: Iterable[Path], limit: int | None = None) -> list[Path]:
    existing_stems = {path.stem for path in json_files}
    missing = [path for path in images if path.stem not in existing_stems]
    if limit is not None:
        missing = missing[:limit]
    return missing


def normalize_bbox(x: float, y: float, width: float, height: float, image_width: int, image_height: int) -> list[float]:
    if image_width <= 0 or image_height <= 0:
        return [0.0, 0.0, 0.0, 0.0]

    x_norm = min(max(0.0, x / image_width * NORMALIZED_SIZE), NORMALIZED_SIZE)
    y_norm = min(max(0.0, y / image_height * NORMALIZED_SIZE), NORMALIZED_SIZE)
    w_norm = min(max(0.0, width / image_width * NORMALIZED_SIZE), NORMALIZED_SIZE - x_norm)
    h_norm = min(max(0.0, height / image_height * NORMALIZED_SIZE), NORMALIZED_SIZE - y_norm)
    return [round(x_norm, 2), round(y_norm, 2), round(w_norm, 2), round(h_norm, 2)]


def _connected_components(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    boxes: list[tuple[int, int, int, int]] = []

    for y in range(height):
        for x in range(width):
            if mask[y, x] == 0 or visited[y, x]:
                continue
            stack = [(x, y)]
            visited[y, x] = True
            min_x = x
            min_y = y
            max_x = x
            max_y = y

            while stack:
                cx, cy = stack.pop()
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < width and 0 <= ny < height and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((nx, ny))
                        min_x = min(min_x, nx)
                        min_y = min(min_y, ny)
                        max_x = max(max_x, nx)
                        max_y = max(max_y, ny)

            boxes.append((min_x, min_y, max_x - min_x + 1, max_y - min_y + 1))

    return boxes


def detect_pedestrian_lights(image_path: str | Path) -> list[dict]:
    image = Image.open(image_path).convert("RGB")
    arr = np.array(image)
    hsv = np.asarray(image.convert("HSV"), dtype=np.float32)

    red_mask = ((hsv[:, :, 0] <= 12) | (hsv[:, :, 0] >= 160)) & (hsv[:, :, 1] >= 0.25) & (hsv[:, :, 2] >= 0.2)
    green_mask = (hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 90) & (hsv[:, :, 1] >= 0.25) & (hsv[:, :, 2] >= 0.2)

    detections: list[dict] = []
    for color_name, mask in (("red", red_mask), ("green", green_mask)):
        connected = _connected_components(mask.astype(bool).astype(np.uint8))
        for x, y, width, height in connected:
            area = width * height
            if area < 20:
                continue
            if width <= 2 and height <= 2:
                continue
            bbox = normalize_bbox(float(x), float(y), float(width), float(height), arr.shape[1], arr.shape[0])
            detections.append({"bbox": bbox, "state": color_name})

    if not detections:
        return []

    merged: list[dict] = []
    for detection in sorted(detections, key=lambda item: (item["bbox"][0], item["bbox"][1])):
        if not merged:
            merged.append(detection)
            continue

        previous = merged[-1]
        prev_bbox = previous["bbox"]
        curr_bbox = detection["bbox"]
        if (
            abs(curr_bbox[0] - prev_bbox[0]) < 30
            and abs(curr_bbox[1] - prev_bbox[1]) < 30
            and abs(curr_bbox[2] - prev_bbox[2]) < 50
            and abs(curr_bbox[3] - prev_bbox[3]) < 50
        ):
            if detection["state"] == previous["state"]:
                prev_bbox[2] = max(prev_bbox[2], curr_bbox[2])
                prev_bbox[3] = max(prev_bbox[3], curr_bbox[3])
            else:
                merged.append(detection)
        else:
            merged.append(detection)

    return merged


def process_directory(directory: str | Path, limit: int = 0) -> dict:
    directory = Path(directory)
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Directory does not exist: {directory}")

    images = list_image_files(directory)
    json_files = list_json_files(directory)
    missing_images = find_missing_images(images, json_files, limit=limit if limit > 0 else None)

    processed: list[str] = []
    for image_path in missing_images:
        lights = detect_pedestrian_lights(image_path)
        payload = {"traffic_lights": lights}
        output_path = image_path.with_suffix(".json")
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        processed.append(image_path.name)

    return {
        "directory": str(directory),
        "total_images": len(images),
        "total_json_files": len(json_files),
        "missing_images": len(missing_images),
        "images_processed": len(processed),
        "processed_files": processed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="List images, find missing JSON annotations, and write traffic-light annotations.")
    parser.add_argument("directory", help="Directory containing images and sidecar JSON annotation files.")
    parser.add_argument("--limit", type=int, default=0, help="Number of missing images to process. Defaults to all missing images.")
    args = parser.parse_args()

    result = process_directory(args.directory, limit=args.limit)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
