# File duplication finder

Scans a directory for files with identical content.
For standard files, it uses SHA-256 binary hashing.
For PDF files, it extracts the internal text and hashes the text content,
allowing it to group PDFs that look the same but have different metadata.
