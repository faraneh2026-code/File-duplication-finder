# Contributing to File Duplication Finder

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/<your-username>/file-duplication-finder.git
cd file-duplication-finder

# (Optional) Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt
```

## Running Locally

```bash
python find_duplicates.py /path/to/any/folder
```

## Running with Docker

```bash
docker build -t file-dup-finder .
docker run --rm -v /path/to/folder:/data file-dup-finder /data
```

## Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:
- Steps to reproduce
- Expected vs. actual behavior
- Python version and OS
