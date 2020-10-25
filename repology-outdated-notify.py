#! /usr/bin/env python3
"""Outdated package notification script for Repology maintainers.

Regularly polls the Atom feed for outdated packages of a given maintainer on
Repology, and notifies when a new outdated package is detected. Two mechanisms
are supported for notifications:
  - Email (via sendmail)
  - GitHub issue creation (using a personal token)

SPDX-License-Identifier: MIT
"""

import argparse
import collections
import dataclasses
import email.message
import feedparser  # type: ignore
import getpass
import io
import logging
import re
import requests
import subprocess
import sys
import time
import urllib.parse

from typing import Deque, Iterable, Sequence


@dataclasses.dataclass
class Update:
    repository: str
    package: str
    old_version: str
    new_version: str
    details_url: str

    def __repr__(self) -> str:
        return f"<({self.repository}) {self.package}: {self.old_version} -> {self.new_version}>"


class RepologyPoller:
    def __init__(self, *, maintainer: str, repository: str):
        self.maintainer = maintainer
        self.repository = repository

        self.seen_ids: Deque[str] = collections.deque(maxlen=500)
        self.title_re = re.compile(r"^(\S+) (\S+) is outdated by (\S+)$")

    @property
    def feed_url(self) -> str:
        maintainer = urllib.parse.quote(self.maintainer)
        repository = urllib.parse.quote(self.repository)
        return f"https://repology.org/maintainer/{maintainer}/feed-for-repo/{repository}/atom"

    def check_for_updates(self) -> Iterable[Update]:
        feed = feedparser.parse(self.feed_url)
        first_run = len(self.seen_ids) == 0
        for entry in feed.entries:
            if entry.id in self.seen_ids:
                continue
            self.seen_ids.append(entry.id)
            if first_run:
                continue
            if entry.category != "outdated":
                continue

            m = self.title_re.match(entry.title)
            if m is None:
                logging.error("Could not parse entry title: %r", entry.title)
                continue

            yield Update(
                repository=self.repository,
                package=m.group(1),
                old_version=m.group(2),
                new_version=m.group(3),
                details_url=entry.link,
            )


def send_email_notification(recipient: str, update: Update):
    mail = email.message.EmailMessage()
    # socket.getfqdn returns 'localhost' on NixOS.
    fqdn = (
        subprocess.check_output(["hostname", "--fqdn"]).decode("utf-8").strip()
    )
    mail["From"] = f"Repology Updater <{getpass.getuser()}@{fqdn}>"
    mail["To"] = recipient
    mail[
        "Subject"
    ] = f"Outdated package: ({update.repository}) {update.package}: {update.old_version} -> {update.new_version}"
    mail.set_content(f"Details: {update.details_url}")

    subprocess.run(["sendmail"], input=bytes(mail), check=True)


def send_github_notification(repo: str, token: str, update: Update):
    url = f"https://api.github.com/repos/{repo}/issues"
    auth = {"Authorization": f"token {token}"}
    payload = {
        "title": f"({update.repository}) {update.package}: {update.old_version} -> {update.new_version}",
        "body": f"[Details]({update.details_url})",
    }
    r = requests.post(url, json=payload, headers=auth)
    if r.status_code != 201:
        logging.error(
            "Unexpected GitHub response code %d: %s", r.status_code, r.json()
        )


def main(argv: Sequence[str]) -> int:
    logging.getLogger("").setLevel(logging.INFO)

    parser = argparse.ArgumentParser(
        prog=argv[0],
        description="Notifies of outdated maintainer packages on Repology.",
    )
    parser.add_argument(
        "-m",
        "--maintainer",
        required=True,
        type=str,
        help="Email address of the maintainer to poll.",
    )
    parser.add_argument(
        "-r",
        "--repository",
        required=True,
        type=str,
        help="Repology repository to poll updates from.",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=int,
        default=300,
        help="Polling interval, in seconds.",
    )
    parser.add_argument(
        "-e", "--email", type=str, help="Email address to notify."
    )
    parser.add_argument(
        "-g",
        "--github-repo",
        type=str,
        help="GitHub repository on which to create a notification issue. Example: delroth/maintained-packages.",
    )
    parser.add_argument("-t", "--token", type=str, help="GitHub access token.")
    args = parser.parse_args(argv[1:])

    if args.github_repo is not None and args.token is None:
        parser.error("Token (-t) is required if using GitHub notifications.")
        return 1

    poller = RepologyPoller(
        maintainer=args.maintainer, repository=args.repository,
    )
    while True:
        try:
            logging.info("Polling for updates")
            for update in poller.check_for_updates():
                logging.info("Update found: %r", update)
                if args.email:
                    send_email_notification(args.email, update)
                if args.github_repo:
                    send_github_notification(
                        args.github_repo, args.token, update
                    )
        except Exception:
            logging.exception("Error occured during polling cycle")

        time.sleep(args.interval)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
