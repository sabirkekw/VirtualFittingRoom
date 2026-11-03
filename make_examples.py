"""Own synthetic fixtures: schematic mannequin and transparent T-shirt."""
import json
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    folder = Path(__file__).parent / "examples"
    folder.mkdir(exist_ok=True)
    body = Image.new("RGB", (400, 600), (244, 244, 241))
    d = ImageDraw.Draw(body)
    d.ellipse((145, 35, 255, 145), fill=(211, 179, 150))
    d.rectangle((175, 125, 225, 175), fill=(211, 179, 150))
    d.polygon([(130, 160), (270, 160), (295, 355), (105, 355)],
              fill=(211, 179, 150))
    d.line([(130, 165), (95, 255), (80, 365)], fill=(211, 179, 150), width=35)
    d.line([(270, 165), (305, 255), (320, 365)], fill=(211, 179, 150), width=35)
    d.polygon([(105, 350), (295, 350), (280, 560), (220, 560),
               (200, 410), (180, 560), (120, 560)], fill=(67, 76, 90))
    body.save(folder / "person.png")
    shirt = Image.new("RGBA", (200, 240), (0, 0, 0, 0))
    d = ImageDraw.Draw(shirt)
    d.polygon([(50, 30), (75, 18), (100, 35), (125, 18), (150, 30),
               (192, 85), (160, 108), (145, 85), (150, 225), (50, 225),
               (55, 85), (40, 108), (8, 85)], fill=(36, 102, 156, 255))
    for y in (95, 125, 155, 185):
        d.rectangle((56, y, 144, y + 7), fill=(222, 235, 242, 255))
    shirt.save(folder / "shirt.png")
    for name, points in [("straight", [[130, 160], [270, 160]]),
                         ("tilted", [[120, 175], [275, 145]]),
                         ("invalid", [[130, 160], [130, 160]])]:
        data = dict(attempt_id=name, product_id="TSHIRT-001", asset_id="front-v1",
                    person="person.png", garment="shirt.png",
                    person_anchors=points, garment_anchors=[[50, 30], [150, 30]])
        (folder / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
