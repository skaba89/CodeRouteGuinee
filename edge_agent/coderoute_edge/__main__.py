from __future__ import annotations

import uvicorn

from .app import create_app
from .config import EdgeAgentConfig


def main() -> None:
    config = EdgeAgentConfig.from_env()
    kwargs = {
        "host": config.bind_host,
        "port": config.bind_port,
        "log_level": "info",
        "proxy_headers": False,
        "server_header": False,
    }
    if not config.allow_insecure_http:
        kwargs["ssl_certfile"] = str(config.tls_cert_path)
        kwargs["ssl_keyfile"] = str(config.tls_key_path)
    uvicorn.run(create_app(config=config), **kwargs)


if __name__ == "__main__":
    main()
