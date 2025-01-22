# Repology Outdated Package Notifier

[Repology]: https://repology.org

A simple script which polls the Atom feed of a maintainer from [Repology] and
sends notifications for outdated packages through three mechanisms:

1. **Email** (via `sendmail`)
2. **GitHub Issues** (using a personal access token)
3. **Stdout** (via `--local` flag and service logs)

## Prerequisites

- `sendmail` installed and available in the system's `PATH` (for email
  notifications).
- A GitHub personal access token with `repo` scope (for GitHub issue
  notifications).

## License

This project is licensed under the MIT license, following upstream. Please see
[LICENSE](./LICENSE) for more details.
