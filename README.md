# copilot_image_skill

This project provides a small Python-based workflow for scanning a directory of images, identifying missing JSON annotation files, and writing pedestrian traffic-light annotations for the selected images.

## Usage

1. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Run the annotation script:
   ```bash
   python scripts/annotate_missing_images.py /path/to/images --limit 10
   ```

The script:
- lists images and JSON sidecars in the target directory,
- finds images missing a JSON file,
- processes up to the requested number of missing images,
- writes the output as `image_name.json` with a `traffic_lights` array.

Example output:
```json
{
  "traffic_lights": [
    { "bbox": [120.0, 230.0, 40.0, 80.0], "state": "green" }
  ]
}
```