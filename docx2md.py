from pathlib import Path
import argparse

from docx import DocxDocument, TagHtmlConverter


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="docx2md")

    parser.add_argument("file_name", type=Path)
    parser.add_argument("-o", "--out-file", type=Path)
    parser.add_argument("--html", action="store_true")

    args = parser.parse_args()

    file_name = Path(args.file_name)
    out_file = Path(args.out_file) if args.out_file else file_name

    doc = DocxDocument()
    if args.html:
        doc.converter = TagHtmlConverter(doc)

    doc.load(file_name)
    doc.write(out_file)



