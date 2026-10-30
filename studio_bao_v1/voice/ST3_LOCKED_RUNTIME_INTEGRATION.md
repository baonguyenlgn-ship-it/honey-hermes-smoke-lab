# Supertonic 3 — isolated runtime integration for Windows LAB

Current scope is PR #8, `studio-bao-v1/windows-preview-20261030`. The earlier verified 10-wheel hash lock at run 40961004139 is now applied to the **actual inference executable path**. CI downloads only SHA-pinned Python 3.12 Windows wheels, creates an isolated virtual environment, installs only from that local wheelhouse with `--no-index --require-hashes`, and verifies NumPy and ONNX Runtime import from the isolated venv before performing inference. The existing generic M1 VI+KO WAV code now fails closed without an explicitly accepted venv and verified lock digest. There is no old global-pip fallback; after waveform/SHA QA the audio files are deleted and only metadata is uploaded.

This test is necessary because prior M1 WAV and 5-request benchmark had used online normal pip with pinned top-level versions but not locked transitive wheel hashes. The change does **not** certify the model license for commercial use; weights remain OpenRAIL-M, generic built-in M1 is not the Owner's likeness, and native VI/KO pronunciation, subjective male premium timbre and customer SLAs require further independent evaluation. The hosted GitHub Python/venv/pip bootstrap itself is not fully hermetically pinned.

Prior PASS: Windows 5 concurrent synthetic M1 requests in run 40960164053, 5/5, 3.8449s batch, 0.8514s model load, 540.55MiB peak working set. Do not extrapolate this to a 5-call real service SLA.

No Production, no deployment, no external communications, no paid inference, no merge.
