# Windows CPython 3.12 wheel hash lock — evidence and boundary

On Github Windows run 40960674628, pip downloaded ten exact pinned wheels and successfully reinstalled with **--require-hashes --no-index --ignore-installed** from the local wheelhouse. All source wheel SHA256 values from actual log are now stored in `requirements-win-py312-hashes.txt`, including transitive packages. No model weights, WAV, customer data or wheels are published.

Overall run 40960674628 **FAILURE**: independent Node verifier incorrectly split CRLF into lines with retained carriage returns, yielding `HASH_LOCK_LINE_MISSING`. It was a verifier defect, not an offline pip install failure. Repair uses platform-neutral `/\r?\n/` and compares generated wheel lock against committed hash manifest; wait for real CI success before accepting.

These hashes bind to Windows x64 + CPython 3.12 wheel builds only; they do not certify upstream safety, future packages, production suitability, license approval, native pronunciation, or premium MC voice. For any future runtime execution require the locked wheelhouse and no-index mode; the earlier M1 benchmark still used normal pip and does not become supply-chain-pinned retroactively.
