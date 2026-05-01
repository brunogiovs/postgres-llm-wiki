# Autovacuum Evolution: PostgreSQL 12 to 18

This directory contains the converted HTML document with links to the upstream PostgreSQL repository.

## Generated Files

- `autovacuum-evolution.html` - HTML document ready to be converted to PDF
- `README.md` - This file

## PDF Generation

To generate a PDF, use any of the following methods:

### Method 1: Using a Browser (Recommended)

Open the HTML file in your browser and use "Print to PDF" or use headless mode:

**Firefox:**
```bash
firefox --headless --print-to-pdf \
  /data/repos/pg-wiki/wiki/shared/output/autovacuum-evolution.html \
  /data/repos/pg-wiki/wiki/shared/output/autovacuum-evolution.pdf
```

**Chrome/Chromium:**
```bash
google-chrome --headless --print-to-pdf \
  /data/repos/pg-wiki/wiki/shared/output/autovacuum-evolution.html \
  /data/repos/pg-wiki/wiki/shared/output/autovacuum-evolution.pdf
```

### Method 2: Using wkhtmltopdf

```bash
apt-get install -y wkhtmltopdf
wkhtmltopdf /data/repos/pg-wiki/wiki/shared/output/autovacuum-evolution.html \
  /data/repos/pg-wiki/wiki/shared/output/autovacuum-evolution.pdf
```

### Method 3: Using pandoc

```bash
apt-get install -y pandoc
pandoc /data/repos/pg-wiki/wiki/shared/output/autovacuum-evolution.html \
  -o /data/repos/pg-wiki/wiki/shared/output/autovacuum-evolution.pdf
```

### Method 4: Manual Browser Method

1. Open `/data/repos/pg-wiki/wiki/shared/output/autovacuum-evolution.html` in your browser
2. Press `Ctrl+P` (or `Cmd+P` on Mac)
3. Select "Save as PDF" as the destination
4. Click "Save"

## Document Features

- ✅ All file paths converted to links pointing to `github.com/postgres/postgres`
- ✅ Source files linked via tree view
- ✅ Commit hashes linked to specific commits
- ✅ Proper styling for print/PDF output (Times New Roman font)
- ✅ Tables, code blocks, and blockquotes properly formatted
- ✅ Footer with document metadata

## Document Details

- **Title:** Autovacuum Evolution: PostgreSQL 12 to 18
- **Generated:** 2025-05-01
- **Source:** PostgreSQL source code analysis from pg-wiki repository
- **Wiki Path:** `wiki/shared/autovacuum-evolution.md`
- **File Size:** ~20KB (HTML)

## Link Examples

The document now includes clickable links such as:

- `raw/postgres-18/src/backend/postmaster/autovacuum.c` → GitHub tree view
- `b07642dbcd` → Specific commit page
- `/data/repos/pg-wiki/raw/postgres-18/...` → GitHub tree view (normalized path)

## Preview

Open the HTML file in your browser to preview the document before converting to PDF.
