import json

from PIL import Image

from scripts.annotate_missing_images import find_missing_images, process_directory


def test_find_missing_images_detects_unannotated_images(tmp_path):
    img1 = tmp_path / "a.jpg"
    img2 = tmp_path / "b.jpg"
    Image.new("RGB", (100, 100), color="white").save(img1)
    Image.new("RGB", (100, 100), color="white").save(img2)
    (tmp_path / "a.json").write_text(json.dumps({"traffic_lights": []}))

    images, json_files = [img1, img2], [tmp_path / "a.json"]
    missing = find_missing_images(images, json_files, limit=10)

    assert missing == [img2]


def test_process_directory_writes_annotations_for_missing_images(tmp_path):
    img_path = tmp_path / "sample.jpg"
    image = Image.new("RGB", (200, 200), color="white")
    image.putpixel((20, 40), (255, 0, 0))
    image.putpixel((40, 40), (255, 0, 0))
    image.putpixel((20, 60), (0, 255, 0))
    image.putpixel((40, 60), (0, 255, 0))
    image.save(img_path)

    result = process_directory(tmp_path, limit=1)

    assert img_path.exists()
    json_path = tmp_path / "sample.json"
    assert json_path.exists()

    payload = json.loads(json_path.read_text())
    assert isinstance(payload.get("traffic_lights", []), list)
    assert result["images_processed"] == 1
