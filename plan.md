# Implementation plan for image-annotation Copilot skill

## 1. Goal and scope

Build a Copilot skill that accepts a directory path and a requested number of images to process, identifies images that do not yet have a JSON annotation, and writes pedestrian-traffic-light annotations for those images only.

Requirements from the spec:
- Input: a directory containing image files and sidecar JSON files.
- The skill must list images and their corresponding JSON files.
- A Python script handles the file discovery and the missing-annotation logic.
- For each image containing pedestrian traffic lights, save a JSON file containing all normalized bounding boxes and their traffic-light states.
- Bounding boxes use a normalized coordinate space where width = 1000 and height = 1000.
- State values are: red, green, or unknown.
- Ignore car traffic lights, signs, and other non-pedestrian objects.
- A single image may contain multiple pedestrian signals; the skill records every relevant detection in the same JSON file.

### LLM-based classification option

Yes, this is possible in a Copilot skill if the underlying model is multimodal and can receive image input directly. In that case, the skill can use the LLM as the classification engine for pedestrian traffic lights instead of relying only on a hand-written color heuristic.

The most practical architecture is a hybrid one:
- Python handles file discovery, missing-image selection, and JSON writing.
- The LLM handles the perceptual classification step, where it receives the image and a strict schema request.
- A fallback heuristic remains useful as a safety net if the LLM cannot interpret the image or if the runtime is text-only.

If the skill environment exposes only a text-based LLM without image input, then true visual classification is not possible through the model alone. In that situation, the classification must remain a local image-processing heuristic or a separate vision service must be invoked.
## 2. Confirmed behavior decisions

The following decisions are now fixed for the implementation:
- The JSON sidecar for an image uses the same basename as the image.
- One image may contain multiple pedestrian traffic lights; the JSON will include all relevant lights for that image.
- The coordinate system is normalized to 0..1000 for x/y/width/height, using the image's full width and height.
- The skill processes the first N images missing JSON files, where N is the value passed in by the caller.
- The file inventory includes only supported image extensions, such as .jpg, .jpeg, .png, .bmp, .webp.
- If a visible signal cannot be identified reliably, the bounding box is still written with `state: "unknown"`.
- The scan is limited to the selected directory (no recursive search unless explicitly expanded later).

## 3. Proposed architecture

### 3.1 Skill interface
- Expose the skill with arguments:
  - directory: root folder to scan
  - limit: number of missing-image annotations to create
- The skill should report an inventory summary:
  - total images found
  - total JSON files found
  - missing-image count
  - images selected for processing

### 3.2 Python helper script
- Create a Python script, for example: `scripts/annotate_missing_images.py`
- Responsibilities:
  1. Enumerate image files in the target directory.
  2. Match image basenames against existing JSON files.
  3. Compute the set of images missing a JSON annotation.
  4. Select up to `limit` images from that set.
  5. Run the per-image detection/annotation logic.
  6. Write output JSON files for the selected images.

### 3.3 Detection and annotation pipeline

The classification step should be performed in the mode supported by the runtime:

A. If the skill has a multimodal LLM with image input:
- The image is passed to the LLM together with a strict instruction such as:
  - identify every pedestrian traffic light in the scene,
  - ignore vehicle lights and signs,
  - return bounding boxes normalized to 0..1000 coordinates,
  - return state as `red`, `green`, or `unknown`.
- The model responds with structured JSON matching the required schema.
- The Python layer validates the JSON and writes it to disk.

B. If the runtime does not expose image input to the model:
- Use a local heuristic as a fallback for candidate detection and light-color segmentation.
- The LLM can still be used in a second pass for validation or to confirm ambiguous cases.
- This is less accurate but still usable when true vision is unavailable.

### 3.4 Model choice and capability requirement

The relevant implementation requirement is not just “LLM access,” but “multimodal LLM access” with the ability to see the image content directly. That capability determines whether the LLM can classify traffic lights robustly from the raw image.

If the skill is running in a general Copilot environment with image-aware model access, this is feasible and desirable.

If the environment is text-only, the LLM cannot reliably perform the visual classification. In that case, the final solution must fall back to a local image-processing method or a separate external vision model.

### 3.5 Data model

Recommended JSON structure for each image:

```json
{
  "traffic_lights": [
    { "bbox": [x, y, width, height], "state": "red" },
    { "bbox": [x2, y2, width2, height2], "state": "green" }
  ]
}
```

If a visible signal cannot be identified reliably, keep the box and set:

```json
{
  "traffic_lights": [
    { "bbox": [x, y, width, height], "state": "unknown" }
  ]
}
```

This format matches the clarified requirement that a single image may contain multiple pedestrian lights and that all relevant detections are recorded in the same JSON file.

## 4. Implementation phases

### Phase 1: repo scaffolding
- Create a minimal project layout:
  - `scripts/`
  - `skill/` or skill manifest files if needed
  - `README.md` and `plan.md`
- Add Python requirements for image processing, such as OpenCV, Pillow, and any ML/detection dependency required for the chosen detector.

### Phase 2: inventory and missing-file logic
- Implement directory scanning.
- Map image files to JSON files by basename.
- Detect which images have no annotation and select the first N.
- Add logging and dry-run output for inspection.

### Phase 3: pedestrian-traffic-light detection
- Choose the model or CV pipeline:
  - rule-based detection using image heuristics, or
  - a lightweight ML detector if the dataset requires higher accuracy
- Validate false positive filtering: ignore car lights, road signs, and non-pedestrian signals.
- Convert detected pixel coordinates to normalized 0..1000 coordinates.

### Phase 4: state recognition
- Map detected signal color to one of the required states: `red`, `green`, or `unknown`.
- Add logic to fall back to `unknown` when color cannot be confidently identified.

### Phase 5: JSON writing and validation
- Write sidecar JSON files next to each image.
- Validate that the JSON is well-formed and matches the required schema.
- Ensure no unrelated object positions are written.

### Phase 6: integration and verification
- Run the script on a sample directory.
- Confirm that:
  - only missing JSONs are filled
  - the correct number of files are processed
  - only pedestrian lights are annotated
  - bounding boxes are normalized to 1000x1000 scale

## 5. Resolved decisions

The following decisions are now fixed and will guide implementation:
1. The JSON file contains all pedestrian traffic-light detections for the image in a `traffic_lights` array.
2. A single image may have multiple pedestrian lights, and all boxes/states are recorded.
3. If the signal color is uncertain, write the detection with `state: "unknown"`.
4. The scan is limited to the selected folder only.
5. The limit parameter means the maximum number of missing JSON files to annotate.
6. The classification step should use the LLM if and only if the skill runtime supports image input; otherwise a fallback heuristic remains necessary.

## 6. Remaining information needed before implementation

Before finalizing the production design, confirm the following:
1. Is the skill runtime connected to a multimodal LLM that can accept an image as input?
2. Can the LLM return structured JSON with bounding boxes and state values in a reproducible schema?
3. If the model is only text-based, is a separate external vision model allowed as a fallback?
4. Is the goal to use the LLM for all classification, or to use it only for ambiguous cases after local detection?

## 7. Verification checklist

The implementation is complete when all of the following are true:
- The Python script correctly inventories images and JSON files.
- It identifies only images without JSON output.
- It respects the processing limit.
- Each processed image gets a valid JSON annotation file.
- Bounding box coordinates are normalized to a 1000x1000 coordinate system.
- Only pedestrian traffic lights are included.
- State is reported as red, green, or unknown.
- Existing JSON files are left unchanged.

## 8. Recommended next step

After the open questions are answered, implement the directory-scanning script first, then add the classification pipeline and JSON writing logic, followed by validation against a small representative sample of images.
