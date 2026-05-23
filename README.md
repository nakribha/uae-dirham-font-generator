# UAE Dirham Symbol Font Generator

Version: `v1.0.0`

Generate fallback TTF fonts for the official UAE Dirham currency symbol at Unicode `U+20C3`.

Use this when your app, website, POS system, invoice, PDF, or receipt flow needs the UAE Dirham symbol, but your current font does not support it yet.

The generated fonts map the symbol to `U+20C3 UAE DIRHAM SIGN`.

They do not use private-use code points such as `U+E000`.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python build_all.py
```

Before running, put exactly one official UAE Dirham SVG and one or more `.ttf` / `.otf` font files into `input/`.

Generated fallback fonts are written to `output/`.

## Why This Exists

The UAE Dirham symbol is new.

Many operating system fonts, mobile platform fonts, and project fonts do not yet contain `U+20C3`.

If an app renders `U+20C3` without a font that supports it, users may see a missing glyph box.

This tool creates small fallback fonts that contain the dirham symbol at `U+20C3`. Your app can continue using its normal brand font for text and numbers, and use the generated fallback font only for the dirham symbol.

## Who This Is For

Use this project if you need to replace `AED` text with the official UAE Dirham symbol and one of these is true:

- your current app font does not support `U+20C3`
- your operating system font fallback shows a missing glyph box
- your design system needs the symbol to match existing typography
- your Flutter, web, invoice, receipt, or PDF output needs a font-based symbol instead of an image icon
- you want a fallback font that uses the real Unicode code point, not a private-use icon-font mapping

## Important License Notes

This repository intentionally does **not** include:

- third-party font files
- generated derivative fonts
- Central Bank UAE symbol assets

You must provide your own input files and have the required rights to use them.

Do not commit third-party fonts or generated derivative fonts unless you have redistribution rights.

Download the official symbol asset from the Central Bank UAE source:

https://centralbank.ae/media/ryxjtjnr/dirham-currency-symbol-svg.zip

Review the official guidelines:

https://www.centralbank.ae/media/e4ebcgtb/the_guidelines_for_the_national_currency_symbol_uae_dirham_english.pdf

## Folder Structure

```text
dirham-font-generator/
  input/
    .gitkeep
  output/
    .gitkeep
  build_all.py
  requirements.txt
  README.md
  LICENSE
```

## Inputs

Put exactly one `.svg` file in `input/`.

Put one or more `.ttf` or `.otf` reference fonts in `input/`.

The script generates one UAE Dirham fallback font for each input font.

Example:

```text
input/
  Dirham Currency Symbol - Black.svg
  brand_regular.ttf
  brand_italic.ttf
  brand_light.ttf
  brand_semibold.ttf
  brand_bold.ttf
  brand_bold_italic.ttf
```

## Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Generate Fonts

```bash
python build_all.py
```

Generated files are written to `output/`.

The script prints its version when it runs.

## Outputs

Typical output:

```text
output/UaeDirhamFallback-regular.ttf
output/UaeDirhamFallback-regular-italic.ttf
output/UaeDirhamFallback-light.ttf
output/UaeDirhamFallback-semibold.ttf
output/UaeDirhamFallback-bold.ttf
output/UaeDirhamFallback-bold-italic.ttf
output/dirham-font-variants-preview.png
```

The exact generated variant names depend on the input font metadata and file names.

## How It Works

The script reads the official SVG path.

It maps that outline to Unicode `U+20C3`.

It reads each input reference font and copies key font metrics:

- units per em
- ascender
- descender
- line gap
- cap height
- x-height

It then generates a minimal fallback font for each reference font.

The fallback font contains only the required UAE Dirham symbol glyph and minimal font metadata.

## Style Adaptation

The script detects style from the reference font file name and font metadata.

Current behavior:

- Thin, ExtraLight, Light, and Regular keep the official outline weight.
- Italic and Oblique inputs apply a controlled slant.
- Medium applies light controlled outline emboldening.
- SemiBold and DemiBold inputs apply moderate controlled outline emboldening.
- Bold applies stronger controlled outline emboldening.
- ExtraBold, UltraBold, Black, and Heavy apply the strongest controlled outline emboldening.

Italic detection is independent from weight detection.

Examples:

- `Light Italic` becomes `UaeDirhamFallback-light-italic.ttf`.
- `Bold Italic` becomes `UaeDirhamFallback-bold-italic.ttf`.
- `Black` becomes `UaeDirhamFallback-black.ttf`.

For Medium and heavier inputs, the script preserves the internal clearspace of the official symbol so the two horizontal bars do not collapse at small sizes.

Very heavy styles such as ExtraBold, Black, and Heavy still require visual review. Automated emboldening can preserve structure, but it cannot replace type design approval.

## Validation

Open `output/dirham-font-variants-preview.png` for a quick visual review.

Verify that:

- the symbol renders without a missing glyph box
- the symbol appears to the left of the number
- the symbol baseline aligns with the number
- all required weights and styles are legible
- the two horizontal bars remain visually distinct

Browser-based HTML previews are intentionally not generated. Browser font fallback and local file loading behavior differ across Chrome, Safari, and operating systems. The generated PNG preview uses the generated font files directly and is the canonical quick visual check.

## App Usage Example

Use the generated font as a fallback font.

For example, in Flutter:

```dart
ThemeData(
  fontFamily: 'YourBrandFont',
  fontFamilyFallback: const [
    'UaeDirhamFallback',
  ],
)
```

Use Unicode `U+20C3` in text:

```dart
const uaeDirhamSymbol = '\u20C3';
```

Your main font renders normal text and numbers.

The fallback font renders the dirham symbol.

## Related Search Terms

- UAE Dirham symbol font
- AED symbol replacement
- UAE currency symbol
- UAE Dirham Unicode
- U+20C3 font fallback
- Flutter UAE Dirham symbol
- official UAE Dirham currency symbol
- UAE Dirham TTF generator

## Disclaimer

This project is a font generation utility.

It does not grant rights to use or redistribute any third-party font or official asset.

Users are responsible for compliance with font licenses, asset licenses, brand guidelines, and regulatory requirements.
