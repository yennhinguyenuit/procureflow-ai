# Third-party model and runtime

ProcureFlow's application code is MIT licensed. Third-party model weights and runtime binaries retain their own licenses; the project does not claim to train or own the base language model.

- **Qwen2.5 1.5B Instruct GGUF**: pretrained model from [Qwen's official repository](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF), Apache 2.0. The installer retains its license at `models/QWEN-LICENSE.txt`. The selected Q4_K_M file is checked against SHA-256 `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`.
- **llama.cpp**: local CPU inference runtime from [ggml-org](https://github.com/ggml-org/llama.cpp), MIT licensed. Its release archive's published SHA-256 digest is verified before extraction. Installation provenance is saved in `runtime/local-ai-manifest.json`.
- **Inter**: locally bundled font package from Fontsource, under its upstream SIL Open Font License. See `frontend/node_modules/@fontsource/inter/LICENSE` after installing frontend dependencies.

The setup command downloads third-party artifacts directly to ignored local folders. They are not committed into this repository. Installation needs internet access; running the model thereafter does not require a cloud inference service.
