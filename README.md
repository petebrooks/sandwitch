# sandwitch

## Installation

Install the required libraries:

```sh
poetry install
```

## Usage

### Basic Usage


```sh
python main.py /path/to/root_dir /path/to/output_dir
```

### Options

- `root_dir`: Root directory containing layer directories (`layer_0`, `layer_1`, ...)
- `output_dir`: Directory to save the composited videos
- `--width`: Target video width (default: max)
- `--height`: Target video height (default: max)
- `--fps`: Target frame rate (default: 30)
- `--dry-run`: Print the number of output videos that would be created without creating them
- `--output-format`: Output video format (default: mp4)
- `--file-name-prefix`: Prefix for output video file names (default: composite)
- `--log-file`: Log file to capture detailed output
- `--verbose`: Enable verbose mode for more detailed output

### Examples

**Standard Execution:**

```sh
python main.py /path/to/root_dir /path/to/output_dir --width 1280 --height 720 --fps 24
```

**Dry Run:**

```sh
python main.py /path/to/root_dir /path/to/output_dir --dry-run
```

**With Custom Output Format and Prefix:**

```sh
python main.py /path/to/root_dir /path/to/output_dir --output-format avi --file-name-prefix myvideo
```

**With Logging and Verbose Mode:**

```sh
python main.py /path/to/root_dir /path/to/output_dir --log-file process.log --verbose
```
