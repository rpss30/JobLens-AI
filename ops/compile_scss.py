from __future__ import annotations

from pathlib import Path

import sass


OPS_DIR = Path(__file__).resolve().parent
SCSS_PATH = OPS_DIR / "static" / "scss" / "ops.scss"
CSS_PATH = OPS_DIR / "static" / "css" / "ops.css"


def compile_scss(
    source_path: Path = SCSS_PATH,
    output_path: Path = CSS_PATH,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    compiled_css = sass.compile(
        filename=str(source_path),
        include_paths=[str(source_path.parent)],
        output_style="expanded",
    )
    output_path.write_text(compiled_css, encoding="utf-8")
    return output_path


def main() -> None:
    output_path = compile_scss()
    print(f"Compiled {output_path}")


if __name__ == "__main__":
    main()

