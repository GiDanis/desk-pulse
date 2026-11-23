# Fantacalcio live protocol reference

Protocol and descriptor decoding reference: [andregri/fantacalcio-voti-live-js](https://github.com/andregri/fantacalcio-voti-live-js), copyright 2023 Andrea Grillo, Apache License 2.0 ([text](Apache-2.0.txt)). The descriptor decoding formula in `fantacalcio_live.py` is adapted from `src/api.js`.

`fixtures/fantacalcio-live-2023-24-4.base64` and `fixtures/fantacalcio-live-schema.json` are the reference project's `test_data/protobuf_msg_base64.txt` and `src/proto.json`, downloaded 1 October 2026. They are recorded historical samples, not evidence of a currently active live session.

The Python wire decoder, seasonal cache, selection checks and dashboard integration are implemented in this project.
