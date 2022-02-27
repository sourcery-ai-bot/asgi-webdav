# Overview

![GitHub](https://img.shields.io/github/license/rexzhang/asgi-webdav)
![Docker Image Version (tag latest semver)](https://img.shields.io/docker/v/ray1ex/asgi-webdav/latest)
![Pytest Workflow Status](https://github.com/rexzhang/asgi-webdav/actions/workflows/check-pytest.yml/badge.svg)
[![codecov](https://codecov.io/gh/rexzhang/asgi-webdav/branch/main/graph/badge.svg?token=6D961MCCWN)](https://codecov.io/gh/rexzhang/asgi-webdav)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![LGTM Grade](https://img.shields.io/lgtm/grade/python/github/rexzhang/asgi-webdav)](https://lgtm.com/projects/g/rexzhang/asgi-webdav)
[![Docker Pulls](https://img.shields.io/docker/pulls/ray1ex/asgi-webdav)](https://hub.docker.com/r/ray1ex/asgi-webdav)
[![downloads](https://img.shields.io/github/downloads/rexzhang/asgi-webdav/total)](https://github.com/rexzhang/asgi-webdav/releases)

An asynchronous WebDAV server implementation, Support multi-provider, multi-account and permission control.

## Features

- [ASGI](https://asgi.readthedocs.io) standard
- WebDAV standard: [RFC4918](https://www.ietf.org/rfc/rfc4918.txt)
- Support multi-provider: FileProvider, MemoryProvider
- Support multi-account and permission control
- Support optional home directory
- Full asyncio file IO
- Passed all [litmus(0.13)](http://www.webdav.org/neon/litmus) test, except 2 warning
- Browse the file directory in the browser
- Support HTTP Basic/Digest authentication
- Support response in Gzip/Brotli
- Compatible with macOS finder(WebDAVFS/3.0.0)
- Compatible with Window10 Explorer(Microsoft-WebDAV-MiniRedir/10.0.19043)

## Quick Start

```shell
docker pull ray1ex/asgi-webdav:latest
docker run --restart always -p 0.0.0.0:8000:8000 -v /your/path:/data \
  --name asgi-webdav ray1ex/asgi-webdav
```

### Default Account

|            | value      | description                     |
|------------|------------|---------------------------------|
| username   | `username` | -                               |
| password   | `password` | -                               |
| permission | `["+"]`    | Allow access to all directories |

### View in Browser

![](web-dir-browser-screenshot.png)