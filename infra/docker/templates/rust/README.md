# Rust Service Docker Template

## Build & Run

```bash
cd infra/docker/templates/rust
docker build -t rust-app --build-arg BIN_NAME=app .
docker run -p 8080:8080 rust-app
```

- `BIN_NAME` must match the binary built by your Cargo project (`[[bin]]` name or package name).
- The container expects your service to listen on `PORT` (default 8080) and expose `/health` for the healthcheck.

## Notes

- Multi-stage build produces a small Alpine runtime image.
- Runs as non-root `rustapp` user.
- Install any system deps by extending the builder image and adding the packages you need.
