import argparse

import pytest

from main import _http_url


def test_http_url_accepts_a_direct_https_address() -> None:
    assert _http_url("https://proof.ovh.net/files/10Mb.dat") == "https://proof.ovh.net/files/10Mb.dat"


def test_http_url_unwraps_a_pasted_markdown_link() -> None:
    assert _http_url(
        "[OVH test file](https://proof.ovh.net/files/10Mb.dat)",
    ) == "https://proof.ovh.net/files/10Mb.dat"


def test_http_url_rejects_whitespace_and_non_http_schemes() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="whitespace"):
        _http_url("https://proof.ovh.net/files/10 Mb.dat")
    with pytest.raises(argparse.ArgumentTypeError, match="absolute"):
        _http_url("ftp://proof.ovh.net/files/10Mb.dat")
