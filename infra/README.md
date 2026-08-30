# Infrastructure

Google Cloud project: `villagelensai`.

Initial limits are Cloud Run region `asia-south1`, minimum instances zero,
maximum instances one, request-based billing, and no GPU or Kubernetes
resources. `villagelensai.com` is delegated to Cloudflare, but application DNS
records must remain unset until the temporary Cloud Run URL passes validation.
