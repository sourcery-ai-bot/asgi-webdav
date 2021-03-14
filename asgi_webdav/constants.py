from typing import Optional, Union, NewType
from enum import Enum, IntEnum
from time import time
from uuid import UUID
from dataclasses import dataclass, field
from collections import namedtuple

LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'webdav': {
            'format': '%(asctime)s %(levelname)s: [%(name)s] %(message)s'
        },  # disable datetime in docker
        'uvicorn': {
            'format': '%(asctime)s %(levelname)s: [uvicorn] %(message)s'
        },
    },
    'handlers': {
        'webdav': {
            'class': 'logging.StreamHandler',
            'formatter': 'webdav',
            'level': 'DEBUG',
        },
        'uvicorn': {
            'class': 'logging.StreamHandler',
            'formatter': 'uvicorn',
            'level': 'INFO',
        },
    },
    'loggers': {
        'asgi_webdav': {
            'handlers': ['webdav', ],
            'propagate': False,
            'level': 'DEBUG',
        },
        'uvicorn': {
            'handlers': ['uvicorn', ],
            'propagate': False,
            'level': 'INFO',
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
    'PROPFIND',
    # rfc4918:9.2
    'PROPPATCH',

    # rfc4918:9.3
    'MKCOL',
    # rfc4918:9.4
    'GET', 'HEAD',
    # rfc4918:9.6
    'DELETE',
    # rfc4918:9.7
    'PUT',

    # rfc4918:9.8
    'COPY',
    # rfc4918:9.9
    'MOVE',

    # rfc4918:9.10
    'LOCK',
    # rfc4918:9.11
    'UNLOCK',

    'OPTIONS',
}
DAVMethod = namedtuple('DAVMethodClass', DAV_METHODS)(*DAV_METHODS)


class DAVPath:
    raw: str  # must start with '/' or empty, and not end with '/'
    # weight: int  # len(raw)

    parts: list[str]
    count: int  # len(parts)

    def _update_value(self, parts: list[str], count: int):
        self.raw = '/' + '/'.join(parts)
        self.parts = parts
        self.count = count

    def __init__(
        self, raw: Union[str, bytes, None] = None,
        parts: list[str] = None, count: int = None
    ):
        if raw is None and parts is not None and count is not None:
            self._update_value(parts=parts, count=count)
            return

        elif not isinstance(raw, (str, bytes)):
            raise Exception('Except raw path for DAVPath:{}'.format(raw))

        if isinstance(raw, bytes):
            raw = str(raw, encoding='utf-8')

        if raw[0] != '/':
            raise Exception('Except raw path for DAVPath:{}'.format(raw))

        parts = list()
        for item in raw.split('/'):
            if len(item) == 0:
                continue

            if item == '..':
                try:
                    parts.pop()
                except IndexError:
                    raise Exception(
                        'Except raw path for DAVPath:{}'.format(raw)
                    )
                continue

            parts.append(item)

        self._update_value(parts=parts, count=len(parts))

    @property
    def parent(self) -> 'DAVPath':
        return DAVPath(
            parts=self.parts[:self.count - 1],
            count=self.count - 1
        )

    @property
    def name(self) -> str:
        return self.parts[self.count - 1]

    def startswith(self, path: 'DAVPath') -> bool:
        return self.parts[:path.count] == path.parts

    def get_child(self, parent: 'DAVPath') -> 'DAVPath':
        new_parts = self.parts[parent.count:]
        return DAVPath(
            parts=new_parts,
            count=self.count - parent.count
        )

    def add_child(self, child: str) -> 'DAVPath':
        child = child.replace('/', '').replace('..', '')
        return DAVPath(
            parts=self.parts + [child],
            count=self.count + 1,
        )

    def __hash__(self):
        return hash(self.raw)

    def __eq__(self, other):
        return self.raw == other.raw

    def __repr__(self):
        return "DAVPath('{}')".format(self.raw)

    def __str__(self):
        return self.raw


class DAVDepth(Enum):
    d0 = 0
    d1 = 1
    infinity = 'infinity'


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
        s = ', '.join([
            self.path.raw, self.depth.__str__(), self.timeout.__str__(),
            self.expire.__str__(), self.scope.name, self.owner, self.token.hex
        ])
        return "DAVLockInfo({})".format(s)


@dataclass
class DAVPassport:
    """ Distribute Information
    DAVDistributor => DavProvider => provider.implement
    """
    provider: any  # DAVProvider

    src_prefix: DAVPath
    src_path: DAVPath

    dst_path: Optional[DAVPath] = None


DAV_PROPERTY_BASIC_KEYS = {
    'displayname', 'getetag',
    'creationdate', 'getlastmodified',
    'getcontenttype', 'getcontentlength',  # 'getcontentlanguage',
    'resourcetype',

    'encoding',
    # 'supportedlock', 'lockdiscovery'
    # 'executable'
}

DAVPropertyIdentity = NewType(
    # (namespace, key)
    'DAVPropertyIdentity', tuple[str, str]
)
DAVPropertyPatches = NewType(
    'DAVPropertyPatches', list[
        # (DAVPropertyIdentity(sn_key), value, set<True>/remove<False>)
        tuple[DAVPropertyIdentity, str, bool]
    ]
)


class DAVProperty:
    path: DAVPath  # = passport.src_path + child ; child maybe is empty
    is_collection: bool

    # basic: bool
    # basic_keys: list[str]
    basic_data: dict[str, str]

    # extra: bool
    # extra_keys: list[str]
    extra_data: dict[DAVPropertyIdentity, str]
    extra_not_found: list[str]
