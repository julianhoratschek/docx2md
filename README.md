# DOCX to Markdown Converter

A lightweight, pure Python script designed to convert Microsoft Word (`.docx`) files directly into clean GitHub-Flavored Markdown (`.md`).

This project distinguishes itself by directly parsing the internal XML structure (specifically `word/document.xml`) of `.docx` files without relying on heavy third-party libraries like `python-docx` or `pandoc`. Instead, it leverages Python's built-in modules such as `zipfile` and `re` for efficient and dependency-free conversion.


## ✨ Key Features & Benefits

*   **Lightweight & Dependency-Free**: Utilizes only standard Python libraries (`zipfile`, `re`), avoiding external dependencies and ensuring a minimal footprint.
*   **Direct DOCX Parsing**: Directly reads and interprets the XML structure within `.docx` files for precise control over the conversion process.
*   **GitHub-Flavored Markdown Output**: Generates clean, readable Markdown (`.md`) optimized for rendering on platforms like GitHub.
*   **Pure Python Implementation**: Entirely implemented in Python, ensuring broad compatibility across various operating systems.
*   **HTML Conversion Capability**: Although primarily focused on Markdown, the modular architecture (featuring `TagHtmlConverter`) supports conversion to HTML as well.
*   **Foundation for Control**: Provides a robust foundation for fine-grained control over document parsing, styling, and output formatting.


## 🚀 Prerequisites & Dependencies

To run `docx2md`, you only need:

*   **Python 3.10**: This project requires a Python 3 environment.

**No external dependencies are required**; all necessary modules are part of Python's standard library.


## ⚙️ Installation & Setup Instructions

Since `docx2md` is a script, not a package, installation is straightforward:

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/julianhoratschek/docx2md.git

    ```

2.  **Navigate to the project directory**:
    ```bash
    cd docx2md

    ```

3.  **Ensure Python is installed**:
    Verify your Python version (3.x is required):
    ```bash
    python --version

    ```

You are now ready to use the converter!


## 🛠️ Commandline Options


| Option             | Parameter | Description                        | Default       |
| ------------------ | --------- | ---------------------------------- | ------------- |
| `-o`, `--out-file` | filename  | Define output file                 | input_file.md |
| `--html`           |           | Export to HTML instead of markdown | False         |
| `-s`, `--style`    | filename  | Use `filename` as css stylesheet   | `style.css`   |


If no output file is given, `docx2md` defaults to the input filename with
changed extension (`.md` or `.html`)


## 💡 Usage Examples

The primary entry point for `docx2md` is the `docx2md.py` script.


### Command-Line Usage

To convert a `.docx` file to Markdown:

```bash
python docx2md.py -o output.md input.docx

```

To convert a `.docx` file to HTML:

```bash
python docx2md.py --html -o output.html input.docx

```

## 📄 License Information

This project currently **does not have an explicit license specified**. Users are advised to contact the owner, `julianhoratschek`, for licensing terms for any use beyond personal evaluation.


## 🙏 Acknowledgments

This README was generated with the help of AI.
