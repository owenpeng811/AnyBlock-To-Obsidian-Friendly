# AnyBlock-To-Obsidian-Friendly

A refined and enhanced version of the Anytype-to-Markdown exporter, specifically optimized for high-fidelity Obsidian integration. This tool transforms complex Anytype Anyblock JSON exports into clean, standardized Markdown, with a focus on preserving critical metadata, relations, and visual diagrams.

## 🚀 Key Enhancements in this Fork

- **Global Relation & Link Resolution**: Translates cryptic Anytype hashes (`bafy...`) into human-readable names for **Object Types**, **Relations**, and **Links**. These are automatically wrapped in `[[Wikilinks]]`, transforming broken IDs into a fully navigable Obsidian vault.
- **Obsidian Dataview Integration**: Automatically converts Anytype **Sets and Collections** into native Obsidian Dataview query blocks (`TABLE` or `LIST`), utilizing resolved names to ensure your queries work out of the box.
- **Hierarchical Folder Structure**: Automatically organizes exported files into subfolders based on their **Object Type** (e.g., `Page/`, `Task/`, `Note/`), keeping your vault logically structured and tidy.
- **Mermaid Rendering Fix**: Correctly identifies and wraps Anytype's visual diagrams into standard ` ```mermaid ` code blocks, ensuring they render properly in Obsidian and other Markdown tools.
- **Anytype Deep Links**: Adds an `anytype` link in the YAML frontmatter, allowing you to jump back to the original object in Anytype with one click.
- **Standardized Tagging**: Normalizes Anytype tags by renaming fields to `tags` and replacing internal spaces with hyphens, ensuring full compatibility with Markdown tagging systems.
- **Robust Encoding Support**: Integrated `chardet` to automatically detect and handle JSON files with varying encodings, ensuring a smooth conversion process without manual intervention.
- **Refined Metadata Cleaning**: Strips redundant system fields while preserving essential relations and timestamps for a clutter-free frontmatter.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [How to Download and Use](#how-to-download-and-use)
- [Configuration](#configuration)
- [Conversion Details](#conversion-details)
- [License](#license)

## Features

- **Full Structural Preservation**: Maintains headers, nested lists, and checkboxes.
- **Advanced Table Parsing**: Accurately parses complex and nested tables, ensuring reliable rendering in any Markdown editor.
- **Formula Support**: Standard LaTeX equation conversion.
- **Attachment Management**: Automatically extracts and links media/files to your Markdown notes.
- **Relation Mapping**: Map Anytype relations to Obsidian-style Bi-links or plain YAML properties.
- **Language Mapping**: Optimizes code blocks by mapping languages like `clike` to `c` and `git` to `diff`.

## Requirements

- **Python 3.7+**
- Python modules: `tqdm`, `pyyaml`, `chardet`

## How to Download and Use

### Step 1: Clone the Repository

Open your terminal and run:
```bash
git clone https://github.com/owenpeng811/AnyBlock-To-Obsidian-Friendly.git
cd AnyBlock-To-Obsidian-Friendly
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Export Anytype Data

1. In Anytype, export your data using the **Anyblock** option (select **JSON** format).
2. Place all exported JSON files into the `anyblock_files` directory of this project.

### Step 4: Run the Conversion

```bash
python3 anyblock_exporter.py
```

Your converted Markdown files will appear in the `markdown_files/` directory, organized by object type.

## Configuration

The `anyblock_exporter/config.yaml` file allows for extensive customization:

- **`ignored_properties`**: List of Anytype relations to skip in the output metadata.
- **`turn_relations_into_obsidian_links`**: Choose between `select`, `all`, or `none` for wrapping properties in `[[Wikilinks]]`.
- **`input_folder` / `output_folder`**: Custom paths for your data.

## Conversion Details

### File Naming
- Filenames are derived from object titles and sanitized for OS compatibility.
- Long filenames (>150 chars) are automatically truncated, with the full title preserved in the frontmatter.

### URI Resolution
- URIs (like `http://`, `telnet://`, `ssh://`) are intelligently detected and protected from Wikilink wrapping to ensure they remain clickable in Obsidian.

---

## Contributing

Created with a focus on data portability and high-fidelity migration. Contributions, bug reports, and feature requests are welcome!

## License

This project is licensed under the terms of the original AnyBlock-To-Markdown license—free to use, modify, and distribute for the benefit of the community.
