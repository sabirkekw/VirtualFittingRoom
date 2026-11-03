"""Procedural 2D preview. Anchors are pixel coordinates after EXIF orientation."""
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PIXELS = 12_000_000
NOTICE = "Визуальный эскиз. Размер, посадка и свойства ткани не определяются."


def load_image(path, garment=False):
    """A1: decode one still PNG/JPEG, normalize orientation, validate alpha."""
    try:
        with Image.open(path) as source:
            if source.format not in {"PNG", "JPEG"}:
                raise ValueError("FORMAT: поддерживаются PNG и JPEG")
            if getattr(source, "n_frames", 1) != 1:
                raise ValueError("FRAMES: требуется одно изображение")
            w, h = source.size
            if w < 2 or h < 2 or w * h > MAX_PIXELS:
                raise ValueError("PIXELS: недопустимое число пикселей")
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGBA")
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValueError("IMAGE: изображение не читается") from exc
    if garment:
        lo, hi = image.getchannel("A").getextrema()
        if lo == 255 or hi == 0:
            raise ValueError("ALPHA: одежде нужен прозрачный фон и видимая область")
    else:
        base = Image.new("RGBA", image.size, "white")
        image = Image.alpha_composite(base, image)
    return image


def validate_anchors(points, size):
    """A1: exactly two finite, distinct points, left-to-right on the screen."""
    if not isinstance(points, (list, tuple)) or len(points) != 2:
        raise ValueError("POINTS: нужны две точки")
    checked = []
    for point in points:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("POINTS: неверная пара координат")
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) for v in point):
            raise ValueError("POINTS: координаты должны быть конечными числами")
        x, y = map(float, point)
        if not (0 <= x < size[0] and 0 <= y < size[1]):
            raise ValueError("BOUNDS: точка за пределами изображения")
        checked.append((x, y))
    (x1, y1), (x2, y2) = checked
    if x2 <= x1 or math.hypot(x2 - x1, y2 - y1) < 2:
        raise ValueError("SPAN: точки слева направо, расстояние не менее 2 px")
    return checked


def similarity(source, target):
    """A2: T(x,y)=(a*x-b*y+tx, b*x+a*y+ty), no shear/reflection."""
    (gx1, gy1), (gx2, gy2) = source
    (px1, py1), (px2, py2) = target
    ux, uy = gx2 - gx1, gy2 - gy1
    vx, vy = px2 - px1, py2 - py1
    denominator = ux * ux + uy * uy
    if denominator <= 0:
        raise ValueError("SPAN: совпадающие точки шаблона")
    a = (ux * vx + uy * vy) / denominator
    b = (ux * vy - uy * vx) / denominator
    scale = math.hypot(a, b)
    if not 0.1 <= scale <= 10:
        raise ValueError("SCALE: масштаб должен быть от 0.1 до 10")
    tx = px1 - a * gx1 + b * gy1
    ty = py1 - b * gx1 - a * gy1
    return a, b, tx, ty


def compose(person, garment, coefficients):
    """A2: inverse mapping with bilinear resampling, then alpha composition."""
    a, b, tx, ty = coefficients
    determinant = a * a + b * b
    inverse = (a / determinant, b / determinant,
               -(a * tx + b * ty) / determinant,
               -b / determinant, a / determinant,
               (b * tx - a * ty) / determinant)
    layer = garment.transform(person.size, Image.Transform.AFFINE, inverse,
                              resample=Image.Resampling.BILINEAR,
                              fillcolor=(0, 0, 0, 0))
    if layer.getchannel("A").getbbox() is None:
        raise ValueError("EMPTY: одежда не попала в кадр")
    return Image.alpha_composite(person, layer).convert("RGB")


def run(config_path, output_dir):
    """One attempt; invalid data raises ValueError before result output."""
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.parent
    person = load_image(root / config["person"])
    garment = load_image(root / config["garment"], garment=True)
    target = validate_anchors(config["person_anchors"], person.size)
    source = validate_anchors(config["garment_anchors"], garment.size)
    coefficients = similarity(source, target)
    result = compose(person, garment, coefficients)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    result.save(output_dir / "preview.png")
    metadata = {
        "attempt_id": config["attempt_id"],
        "asset_id": config["asset_id"], "product_id": config["product_id"],
        "person_anchors": target, "garment_anchors": source,
        "width": result.width, "height": result.height,
        "transform": dict(zip(["a", "b", "tx", "ty"], coefficients)),
        "notice": NOTICE, "preview": "preview.png", "status": "success"
    }
    (output_dir / "result.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config")
    parser.add_argument("output")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.config, args.output), ensure_ascii=False))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
