from typing import Union, NewType, Optional
from enum import Enum, IntEnum
from time import time
from uuid import UUID
from dataclasses import dataclass, field
from collections import namedtuple

import arrow

LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "webdav": {"format": "%(asctime)s %(levelname)s: [%(name)s] %(message)s"},
        "uvicorn": {"format": "%(asctime)s %(levelname)s: [uvicorn] %(message)s"},
        "webdav_docker": {"format": "%(levelname)s: [%(name)s] %(message)s"},
        "uvicorn_docker": {"format": "%(levelname)s: [uvicorn] %(message)s"},
    },
    "handlers": {
        "webdav": {
            "class": "logging.StreamHandler",
            "formatter": "webdav",
            "level": "DEBUG",
        },
        "uvicorn": {
            "class": "logging.StreamHandler",
            "formatter": "uvicorn",
            "level": "INFO",
        },
    },
    "loggers": {
        "asgi_webdav": {
            "handlers": [
                "webdav",
            ],
            "propagate": False,
            "level": "DEBUG",
        },
        "uvicorn": {
            "handlers": [
                "uvicorn",
            ],
            "propagate": False,
            "level": "INFO",
        },
    },
    # 'root': {
    #     'handlers': ['console', ],
    #     'propagate': False,
    #     'level': 'INFO',
    # },
}

DAV_METHODS = {
    # rfc4918:9.1
    "PROPFIND",
    # rfc4918:9.2
    "PROPPATCH",
    # rfc4918:9.3
    "MKCOL",
    # rfc4918:9.4
    "GET",
    "HEAD",
    # rfc4918:9.6
    "DELETE",
    # rfc4918:9.7
    "PUT",
    # rfc4918:9.8
    "COPY",
    # rfc4918:9.9
    "MOVE",
    # rfc4918:9.10
    "LOCK",
    # rfc4918:9.11
    "UNLOCK",
    "OPTIONS",
}
DAVMethod = namedtuple("DAVMethodClass", DAV_METHODS)(*DAV_METHODS)


class DAVPath:
    raw: str  # must start with '/' or empty, and not end with '/'

    parts: list[str]
    count: int  # len(parts)

    def _update_value(self, parts: list[str], count: int):
        self.raw = "/" + "/".join(parts)
        self.parts = parts
        self.count = count

    def __init__(
        self,
        path: Union[str, bytes, None] = None,
        parts: list[str] = None,
        count: int = None,
    ):
        if path is None and parts is not None and count is not None:
            self._update_value(parts=parts, count=count)
            return

        elif not isinstance(path, (str, bytes)):
            raise Exception("Except path for DAVPath:{}".format(path))

        if isinstance(path, bytes):
            path = str(path, encoding="utf-8")

        parts = list()
        for item in path.split("/"):
            if len(item) == 0:
                continue

            if item == "..":
                try:
                    parts.pop()
                except IndexError:
                    raise Exception("Except path for DAVPath:{}".format(path))
                continue

            parts.append(item)

        self._update_value(parts=parts, count=len(parts))

    @property
    def parent(self) -> "DAVPath":
        return DAVPath(parts=self.parts[: self.count - 1], count=self.count - 1)

    @property
    def name(self) -> str:
        if self.count == 0:
            return "/"

        return self.parts[self.count - 1]

    def startswith(self, path: "DAVPath") -> bool:
        return self.parts[: path.count] == path.parts

    def get_child(self, parent: "DAVPath") -> "DAVPath":
        new_parts = self.parts[parent.count :]
        return DAVPath(parts=new_parts, count=self.count - parent.count)

    def add_child(self, child: Union["DAVPath", str]) -> "DAVPath":
        if not isinstance(child, DAVPath):
            child = DAVPath(child)

        return DAVPath(
            parts=self.parts + child.parts,
            count=self.count + child.count,
        )

    def __hash__(self):
        return hash(self.raw)

    def __eq__(self, other):
        return self.raw == other.raw

    def __lt__(self, other):
        return self.raw < other.raw

    def __repr__(self):
        return "DAVPath('{}')".format(self.raw)

    def __str__(self):
        return self.raw


class DAVDepth(Enum):
    d0 = 0
    d1 = 1
    infinity = "infinity"


class DAVTime:
    timestamp: float

    def __init__(self, timestamp: Optional[float] = None):
        if timestamp is None:
            timestamp = time()

        self.timestamp = timestamp
        self.arrow = arrow.get(timestamp)

    def iso_850(self) -> str:
        # https://developer.mozilla.org/zh-CN/docs/Web/HTTP/Headers/Last-Modified
        # Last-Modified:
        #   <day-name>, <day> <month> <year> <hour>:<minute>:<second> GMT
        return self.arrow.format(arrow.FORMAT_RFC850)

    def iso_8601(self) -> str:
        return self.arrow.format(arrow.FORMAT_W3C)

    def __repr__(self):
        return self.arrow.isoformat()


class DAVLockScope(IntEnum):
    """
    https://tools.ietf.org/html/rfc4918
    14.13.  lockscope XML Element
       Name:   lockscope
       Purpose:   Specifies whether a lock is an exclusive lock, or a shared
          lock.

         <!ELEMENT lockscope (exclusive | shared) >
    """

    exclusive = 1
    shared = 2


@dataclass
class DAVLockInfo:
    path: DAVPath
    depth: DAVDepth
    timeout: int
    expire: float = field(init=False)
    scope: DAVLockScope
    owner: str
    token: UUID  # <opaquelocktoken:UUID.__str__()>

    def __post_init__(self):
        self.update_expire()

    def update_expire(self):
        self.expire = time() + self.timeout

    def __repr__(self):
        s = ", ".join(
            [
                self.path.raw,
                self.depth.__str__(),
                self.timeout.__str__(),
                self.expire.__str__(),
                self.scope.name,
                self.owner,
                self.token.hex,
            ]
        )
        return "DAVLockInfo({})".format(s)


@dataclass
class DAVAccount:
    username: str
    permissions: list[str]
    permissions_allow: list[str] = field(default_factory=list)
    permissions_deny: list[str] = field(default_factory=list)

    def __post_init__(self):
        for permission in self.permissions:
            if permission[0] == "+":
                self.permissions_allow.append(permission[1:])
            elif permission[0] == "-":
                self.permissions_deny.append(permission[1:])
            else:
                raise

    def __str__(self):
        return "{}, allow:{}, deny:{}".format(
            self.username, self.permissions_allow, self.permissions_deny
        )


DAV_PROPERTY_BASIC_KEYS = {
    # Identify
    "displayname",
    "getetag",
    # Date Time
    "creationdate",
    "getlastmodified",
    # File Properties
    "getcontenttype",
    "getcontentlength",
    # 'getcontentlanguage',
    # is dir
    "resourcetype",
    "encoding",
    # 'supportedlock', 'lockdiscovery'
    # 'executable'
}

DAVPropertyIdentity = NewType(
    # (namespace, key)
    "DAVPropertyIdentity",
    tuple[str, str],
)
DAVPropertyPatches = NewType(
    "DAVPropertyPatches",
    list[
        # (DAVPropertyIdentity(sn_key), value, set<True>/remove<False>)
        tuple[DAVPropertyIdentity, str, bool]
    ],
)

DEFAULT_FILENAME_CONTENT_TYPE_MAPPING = {
    "README": "text/plain",
    "LICENSE": "text/plain",
    ".gitignore": "text/plain",
    ".coveragerc": "text/plain",
    # docker
    "Dockerfile": "text/plain",
    ".dockerignore": "text/plain",
}

DEFAULT_SUFFIX_CONTENT_TYPE_MAPPING = {
    ".cfg": "text/plain",
    ".md": "text/plain",
    ".toml": "text/plain",
    ".yaml": "text/plain",
    ".yml": "text/plain",
    # code source
    ".php": "text/plain",
}

# https://en.wikipedia.org/wiki/.DS_Store
# https://en.wikipedia.org/wiki/AppleSingle_and_AppleDouble_formats
DIR_BROWSER_MACOS_IGNORE_RULES = r"^\.DS_Store$|^\._"
# https://en.wikipedia.org/wiki/Windows_thumbnail_cache
DIR_BROWSER_WINDOWS_IGNORE_RULES = r"^Thumbs\.db$"
DIR_BROWSER_SYNOLOGY_IGNORE_RULES = "^#recycle$|^@eaDir$"

RESPONSE_DATA_BLOCK_SIZE = 64 * 1024
