#!/usr/bin/python3

import pathlib
import requests
import logging
from dataclasses import dataclass, field
from collections import OrderedDict
from typing import List, Iterator, Tuple, Optional, TypeVar
from ietfdata import datatracker
import paths

T = TypeVar('T')


@dataclass(frozen=True)
class URI:
    uri: str


@dataclass(frozen=True)
class DocURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("https://www.ietf.org/archive/id")


@dataclass(frozen=True)
class URIxml(DocURI):
    extn: str = field(default='.xml', init=False)

    def __post_init__(self) -> None:
        assert pathlib.Path(
            self.uri
        ).suffix == self.extn, f"uri {self.uri} does not end in .xml"


@dataclass(frozen=True)
class xmlFile(URI):
    extn: str = field(default='.xml', init=False)

    def __post_init__(self) -> None:
        assert pathlib.Path(
            self.uri
        ).suffix == self.extn, f"uri {self.uri} does not end in .xml"


@dataclass(frozen=True)
class txtFile(URI):
    extn: str = field(default='.txt', init=False)

    def __post_init__(self) -> None:
        assert pathlib.Path(
            self.uri
        ).suffix == self.extn, f"uri {self.uri} does not end in .xml"


@dataclass(frozen=True)
class URItext(DocURI):
    extn: str = field(default='.txt', init=False)

    def __post_init__(self) -> None:
        assert pathlib.Path(
            self.uri
        ).suffix == self.extn, f"uri {self.uri} does not end in .txt"


WebURITypes = [URIxml, URItext]
FileURITypes = [xmlFile, txtFile]


@dataclass(frozen=True)
class DownloadOptions:
    force: bool = False  # if set to True, override files in cache


class DownloadURI:
    def __init__(self, name: str, rev: str, extn: str) -> None:
        self.name = name
        self.rev = rev
        self.extn = extn.split(sep=',')
        self.webURITypes = [URIxml, URItext]
        self.fileURITypes = [xmlFile, txtFile]

    def _document_stem(self):
        return f"{self.name}-{self.rev}"

    def preferred_doctype(self, webURIBase: str,
                          fileURIBase: str) -> Iterator[Tuple[T, T]]:
        for web_uri, file_uri in zip(self.webURITypes, self.fileURITypes):
            if web_uri.extn in self.extn and web_uri.extn == file_uri.extn:
                yield web_uri( webURIBase + f"/{self._document_stem()}{web_uri.extn}"), \
                        file_uri( fileURIBase + f"/{self.name}/{self.rev}/{self._document_stem()}{file_uri.extn}")

    @property
    def webURI(self) -> T:
        return self._webURI

    @webURI.setter
    def webURI(self, web_uri: T) -> None:
        if type(web_uri) not in self.webURITypes:
            logging.critical( f"type {type(web_uri)} disallowed." \
                    f"Only types {self.webURITypes} allowed." \
                    f"url = {web_uri.uri}")
        assert type(web_uri) in self.webURITypes, f"type {type(web_uri)} disallowed." \
                                                  f"Only types {self.webURITypes} allowed." \
                                                  f"url = {web_uri.uri}"
        self._webURI = web_uri

    @property
    def fileURI(self) -> T:
        return self._fileURI

    @fileURI.setter
    def fileURI(self, file_uri: T) -> None:
        if type(file_uri) not in self.fileURITypes:
            logging.critical( f"type {type(file_uri)} disallowed." \
                    f"Only types {self.fileURITypes} allowed." \
                    f"url = {web_uri.uri}")
        assert type(file_uri) in self.fileURITypes, f"type {type(web_URI)} disallowed." \
                                                    f"Only types {self.webURITypes} allowed." \
                                                    f"url = {web_uri.uri}"
        self._fileURI = file_uri

    def set_used_uri(self, webURI: T, fileURI: T) -> None:
        self.webURI = webURI
        self.fileURI = fileURI


@dataclass
class DownloadClient:
    fslock: paths.FileSysLock
    base_uri: str = "https://www.ietf.org/archive/id"
    dlopts: Optional[DownloadOptions] = field(default_factory=DownloadOptions)

    def __enter__(self) -> None:
        self.session = requests.Session()
        return self

    def __exit__(self, ex_type, ex, ex_tb) -> None:
        self.session.close()
        self.session = None

    def _write_file(self, file_uri: T, data: str) -> bool:
        written = False
        # put  any caching and optional checking in this function
        file_path = pathlib.Path(file_uri.uri)
        file_path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)

        with open(str(file_path), "w") as fp:
            fp.write(data)
            written = True
        return written

    def download_docs(self, urls: List[DownloadURI]) -> List[DownloadURI]:
        docs = list()
        for doc in urls:
            for web_uri, file_uri in doc.preferred_doctype(
                    self.base_uri, str(self.fslock.fs.drafts)):
                dl = self.session.get(web_uri.uri, verify=True, stream=False)
                if dl.status_code != 200:
                    continue

                logging.debug(f"Downloaded url -- {web_uri.uri}")
                if self._write_file(file_uri, dl.text):
                    doc.set_used_uri(web_uri, file_uri)
                    docs.append(doc)
                    logging.debug(f"Written file -- {file_uri.uri}")
                    break
                else:
                    logging.critical(f"Error writing File {file_path.uri}"
                                     f"after downloading url -- {pref_url}")

            else:
                logging.error(f"Could not download any file type for document {doc.name}-{doc.rev}")

        return docs


def download_draft_daterange(
    since: str = "1970-01-01T00:00:00",
    until: str = "2038-01-19T03:14:07",
    dlopts: DownloadOptions = DownloadOptions()
) -> None:

    track = datatracker.DataTracker()
    draft_itr = track.documents(since=since,
                                until=until,
                                doctype=track.document_type("draft"))
    urls = []
    for draft in draft_itr:
        for sub_uri in draft.submissions:
            submission = track.submission(sub_uri)
            if submission:
                urls.append( DownloadURI(submission.name, submission.rev,
                                submission.file_types))

    # Download files
    with paths.FileSysLock( paths.RootWorkingDir(pathlib.Path.cwd() / "test_dir")) as fslock, \
                    DownloadClient( fslock, dlopts= dlopts) as dlclient:
        logging.basicConfig(filename=fslock.fs.log,
                            filemode='a',
                            format="%(asctime)s | %(levelname)s : %(message)s",
                            datefmt="%y-%m-%d %H:%M:%S",
                            level=logging.INFO)
        dlclient.download_docs(urls)


if __name__ == '__main__':
    download_draft_daterange(since="2020-04-03T00:00:00")