from typing import Optional
import json
from enum import Enum
from os import getenv
from logging import getLogger

from pydantic import BaseModel

from asgi_webdav.constants import (
    DEFAULT_FILENAME_CONTENT_TYPE_MAPPING,
    DEFAULT_SUFFIX_CONTENT_TYPE_MAPPING,
    DAVCompressLevel,
    AppArgs,
)


logger = getLogger(__name__)


class User(BaseModel):
    username: str
    password: str
    permissions: list[str]
    admin: bool = False


class HTTPDigestAuth(BaseModel):
    enable: bool = False
    enable_rule: str = ""  # Valid when "enable" is false
    disable_rule: str = "neon/"  # Valid when "enable" is true
    # TODO Compatible with neon


class Provider(BaseModel):
    """
    Home Dir:
        home_dir: True
        prefix: "/~", "/home"
        uri: file:///home/all_user/home

    Shared Dir:
        home_dir: False
        prefix: '/', '/a/b/c', '/a/b/c/'
        uri: file:///home/user_a/webdav/prefix
    """

    prefix: str
    uri: str
    home_dir: bool = False
    readonly: bool = False  # TODO impl


class GuessTypeExtension(BaseModel):
    enable: bool = True
    enable_default_mapping: bool = True

    filename_mapping: dict = dict()
    suffix_mapping: dict = dict()


class TextFileCharsetDetect(BaseModel):
    enable: bool = False
    default: str = "utf-8"


class Compression(BaseModel):
    enable_gzip: bool = True
    enable_brotli: bool = True
    level: DAVCompressLevel = DAVCompressLevel.RECOMMEND

    user_content_type_rule: str = ""


class DirBrowser(BaseModel):
    enable: bool = True
    enable_macos_ignore_rules: bool = True
    enable_windows_ignore_rules: bool = True
    enable_synology_ignore_rules: bool = True

    user_ignore_rule: str = str()


class LoggingLevel(Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class Config(BaseModel):
    # auth
    account_mapping: list[User] = list()  # TODO => user_mapping ?
    http_digest_auth: HTTPDigestAuth = HTTPDigestAuth()

    # provider
    provider_mapping: list[Provider] = list()  # TODO => prefix_mapping ?

    # process
    guess_type_extension: GuessTypeExtension = GuessTypeExtension()
    text_file_charset_detect: TextFileCharsetDetect = TextFileCharsetDetect()

    # response
    compression: Compression = Compression()
    dir_browser: DirBrowser = DirBrowser()

    # other
    logging_level: LoggingLevel = LoggingLevel.INFO
    sentry_dsn: Optional[str] = None

    def update_from_app_args_and_env_and_default_value(self, app_args: AppArgs):
        """
        CLI Args > Environment Variable > Configuration File > Default Value
        """

        # auth
        if app_args.admin_user is not None:
            username = app_args.admin_user[0]
            password = app_args.admin_user[1]
        elif getenv("WEBDAV_PASSWORD") is not None:
            username = getenv("WEBDAV_USERNAME")
            password = getenv("WEBDAV_PASSWORD")
        else:
            username = None
            password = None

        if username is not None:
            user_id = None
            for index in range(len(self.account_mapping)):
                if self.account_mapping[index].username == username:
                    user_id = index
                    break

            if user_id is None:
                account = User(username=username, password=password, permissions=["+"])

                self.account_mapping.append(account)

            else:
                account = self.account_mapping[user_id]
                account.username = username
                account.password = password

                self.account_mapping[user_id] = account

        # auth - default
        if len(self.account_mapping) == 0:
            self.account_mapping.append(
                User(username="username", password="password", permissions=["+"])
            )

        # provider - CLI
        if app_args.root_path is not None:
            root_path_index = None
            for index in range(len(self.provider_mapping)):
                if self.provider_mapping[index].prefix == "/":
                    root_path_index = index
                    break

            root_path_uri = "file://{}".format(app_args.root_path)
            if root_path_index is None:
                self.provider_mapping.append(Provider(prefix="/", uri=root_path_uri))
            else:
                self.provider_mapping[root_path_index].uri = root_path_uri

        # provider - default
        if len(self.provider_mapping) == 0:
            self.provider_mapping.append(Provider(prefix="/", uri="file:///data"))

        # response - default
        if self.guess_type_extension.enable_default_mapping:
            new_mapping = dict()
            new_mapping.update(DEFAULT_FILENAME_CONTENT_TYPE_MAPPING)
            new_mapping.update(self.guess_type_extension.filename_mapping)
            self.guess_type_extension.filename_mapping = new_mapping

            new_mapping = dict()
            new_mapping.update(DEFAULT_SUFFIX_CONTENT_TYPE_MAPPING)
            new_mapping.update(self.guess_type_extension.suffix_mapping)
            self.guess_type_extension.suffix_mapping = new_mapping

        # other - env
        logging_level = getenv("WEBDAV_LOGGING_LEVEL")
        if logging_level:
            self.logging_level = LoggingLevel(logging_level)

        sentry_dsn = getenv("WEBDAV_SENTRY_DSN")
        if sentry_dsn:
            self.sentry_dsn = sentry_dsn


config = Config()


def get_config() -> Config:
    global config
    return config


def update_config_from_file(config_file: str) -> Config:
    global config
    try:
        config = config.parse_file(config_file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        message = "Load config value from file[{}] failed!".format(config_file)
        logger.warning(message)
        logger.warning(e)

    logger.info("Load config value from config file:{}".format(config_file))
    return config


def update_config_from_obj(obj: dict) -> Config:
    global config
    logger.info("Load config value from python object:{}".format(obj))
    config = config.parse_obj(obj)

    return config
