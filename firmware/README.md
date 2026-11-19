# ESP32-S3 telemetry firmware

The firmware reports device-owned health telemetry only. It has no USB HID keyboard, command execution, remote script download, credential collection, or host-control behavior.

Pin assignments: red GPIO 47, green GPIO 36, white GPIO 37. White indicates connection setup, green indicates successful reporting, and red indicates a reporting error.

1. Copy `include/config.example.h` to `include/config.h`.
2. Set Wi-Fi credentials, API base URL, API token, session UUID, and device identifier locally.
3. Run `pio run -d firmware -t upload`.

`config.h` is ignored by Git. HTTP is suitable only on an isolated trusted development network; use TLS-capable deployment for real network operation. Physical behavior has not been verified by repository CI.
