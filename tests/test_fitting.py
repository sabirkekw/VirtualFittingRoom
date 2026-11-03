"""Function tests, with a standard-library procedural test runner."""
import math
import tempfile
from pathlib import Path
from PIL import Image
from fitting import compose, load_image, run, similarity, validate_anchors

ROOT = Path(__file__).resolve().parents[1]


def expect_error(fn, code):
    try:
        fn()
    except ValueError as exc:
        assert str(exc).startswith(code), str(exc)
    else:
        raise AssertionError("Expected error: " + code)


def test_identity():
    assert similarity([(1, 1), (5, 1)], [(1, 1), (5, 1)]) == (1, 0, 0, 0)


def test_known_transform():
    assert similarity([(50, 30), (150, 30)], [(130, 160), (270, 160)]) == (1.4, 0, 60, 118)


def test_tilt_anchor_mapping():
    src, dst = [(50, 30), (150, 30)], [(120, 175), (275, 145)]
    a, b, tx, ty = similarity(src, dst)
    for (x, y), (px, py) in zip(src, dst):
        assert math.isclose(a*x-b*y+tx, px, abs_tol=1e-9)
        assert math.isclose(b*x+a*y+ty, py, abs_tol=1e-9)


def test_coincident():
    expect_error(lambda: validate_anchors([[2, 2], [2, 2]], (20, 20)), "SPAN")


def test_bounds():
    expect_error(lambda: validate_anchors([[1, 1], [20, 1]], (20, 20)), "BOUNDS")


def test_nonfinite():
    expect_error(lambda: validate_anchors([[1, 1], [float("nan"), 2]], (20, 20)), "POINTS")


def test_scale_limit():
    expect_error(lambda: similarity([(0, 0), (2, 0)], [(0, 0), (100, 0)]), "SCALE")


def test_alpha_pixels():
    base = Image.new("RGBA", (8, 8), (255, 255, 255, 255))
    cloth = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    cloth.putpixel((2, 2), (255, 0, 0, 255))
    cloth.putpixel((4, 4), (255, 0, 0, 128))
    out = compose(base, cloth, (1, 0, 0, 0))
    assert out.getpixel((0, 0)) == (255, 255, 255)
    assert out.getpixel((2, 2)) == (255, 0, 0)
    assert out.getpixel((4, 4)) == (255, 127, 127)


def test_bad_images():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "opaque.png"
        Image.new("RGB", (8, 8), "blue").save(path)
        expect_error(lambda: load_image(path, garment=True), "ALPHA")
        path.write_bytes(b"not an image")
        expect_error(lambda: load_image(path), "IMAGE")


def test_pixel_limit():
    import fitting
    old = fitting.MAX_PIXELS
    try:
        fitting.MAX_PIXELS = 10
        expect_error(lambda: load_image(ROOT / "examples/person.png"), "PIXELS")
    finally:
        fitting.MAX_PIXELS = old


def test_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        metadata = run(ROOT / "examples/straight.json", tmp)
        assert (metadata["width"], metadata["height"]) == (400, 600)
        out = Image.open(Path(tmp) / "preview.png")
        assert out.getpixel((0, 0)) == (244, 244, 241)
        assert out.getpixel((200, 240)) == (36, 102, 156)
        assert (Path(tmp) / "result.json").exists()


def test_invalid_no_output():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "attempt"
        expect_error(lambda: run(ROOT / "examples/invalid.json", out), "SPAN")
        assert not out.exists()


def main():
    tests = [(name, fn) for name, fn in globals().items() if name.startswith("test_")]
    for name, fn in tests:
        fn()
        print("PASS", name)
    print(f"RESULT: {len(tests)}/{len(tests)} passed")


if __name__ == "__main__":
    main()
