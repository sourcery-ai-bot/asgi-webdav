from typing import Optional
import json
import xml
from pprint import pprint
from dataclasses import dataclass

import requests
from requests.auth import AuthBase, HTTPBasicAuth, HTTPDigestAuth
import xmltodict


@dataclass
class Connect:
    base_url: str
    method: str
    path: str

    headers: Optional[dict[str, str]]
    auth: AuthBase


def call(conn):
    result = requests.request(
        conn.method, conn.base_url + conn.path, headers=conn.headers, auth=conn.auth
    )
    print("---------------------")
    print(result)
    pprint(result.headers)
    if len(result.content) > 0:
        try:
            pprint(json.loads((json.dumps(xmltodict.parse(result.content)))))
        except xml.parsers.expat.ExpatError:
            pass
    else:
        pprint(result.content)


def server_basic_auth(
    method, path, headers=None, username="username", password="password"
):
    call(
        Connect(
            "http://127.0.0.1:8000",
            method,
            path,
            headers,
            HTTPBasicAuth(username, password),
        )
    )


def server_digest_auth(
    method, path, headers=None, username="username", password="password"
):
    call(
        Connect(
            "http://127.0.0.1:8000",
            method,
            path,
            headers,
            HTTPDigestAuth(username, password),
        )
    )


def main_test_auth():
    server_basic_auth("OPTIONS", "/")
    server_basic_auth("OPTIONS", "/", username="user-hashlib")

    server_basic_auth("OPTIONS", "/", username="user-ldap", password="bad-password")

    server_basic_auth("OPTIONS", "/", username="user-ldap", password="Pass1234")
    # - hit cache
    server_basic_auth("OPTIONS", "/", username="user-ldap", password="Pass1234")
    server_basic_auth("OPTIONS", "/", username="user-ldap", password="Pass1234")

    server_digest_auth("OPTIONS", "/")
    # server_digest_auth("OPTIONS", "/", username="user-digest")


def user_agent_test():
    headers = {"user-agent": "TEST-AGENT"}
    server_digest_auth("GET", "/", headers=headers)


def main():
    # test_apache('PROPFIND', '/home', headers={'depth': '1'})
    # test_apache('PROPFIND', '/.sync')
    # test_apache('PROPFIND', '/litmus', headers={'depth': '0'})
    # test_asgi('PROPFIND', '/litmus')
    # test_asgi('PROPFIND', '/dir1/file1')
    # test_asgi('PROPFIND', '/dir1', headers={'depth': '0'})
    # asgi_server("PROPFIND", "/", headers={"depth": "1"})
    # test_asgi('PROPFIND', '/joplin', headers={'depth': '1'})
    # test_asgi('PROPFIND', '/dir1', headers={'depth': 'infinity'})

    pass


if __name__ == "__main__":
    main_test_auth()
    # user_agent_test()
