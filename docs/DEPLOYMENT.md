# Secure deployment

The default `127.0.0.1` bind address is intentional. For network use:

1. Place Flask behind a maintained TLS reverse proxy.
2. Generate a unique random token of at least 32 bytes and provide it through the environment or a service secret store.
3. Bind only to the authorized laboratory interface and restrict inbound traffic with a host firewall.
4. Run as an unprivileged dedicated account.
5. Store `data/` on an encrypted volume and establish backup and retention procedures.
6. Rotate the token after demonstrations or suspected exposure.
7. Do not enable Flask debug mode or expose the development server directly to untrusted networks.

For production-like deployment, use a maintained WSGI server and configure TLS, request logging with secret redaction, and centralized rate limiting at the proxy.
