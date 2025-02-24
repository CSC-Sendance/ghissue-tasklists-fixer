# ghissue-tasklists-fixer

This serves to to react on Github [removing the "tasklist" feature on April 30th 2025](https://github.blog/changelog/2025-02-18-github-issues-projects-february-18th-update/#tasklist-blocks-will-be-retired-and-replaced-with-sub-issues).

The tool scans existing issues of the configured repository for `tasklist` blocks, removes its markup and scans its content for potential [subissues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues). A potential subissue is a task list item (i.e. starting with `- [ ]` or `- [x]`) that contains a relative (`#<issuenumber>`) or direct (`https://github.com/<owner>/<repo>/<issues>/`) link to another issue. If such a subissue is detected, it is removed from the checkbox list and added as subissue to the scanned issue.

Caveats:

- An issue can only have one parent issue. I.e., if an issue is referenced in tasklists of multiple issues scanned by this tool, the last scanned issue will be the final parent.
- Use on your own risk :)

## Installation

1. Install python 3.x and corresponding pip version
2. `pip install -r requirements.txt`

## Usage

1. Execute `python main.py`

- On very first usage, the script will terminate early but create a (gitignore-d) `config.json`. Fill the json with the pre-defined fields. The `token` is a Github Personal Access Token (PAT) with the necessary permissions to update and modify issues and subissues of the configured repository.

- Afterwards, the configured repository is scanned and the actions performed, as described above.

## config.json

Fields:

- `owner` : the owner organization
- `repo` : the repo to be scanned
- `token` : the Github Personal Access Token (PAT) to access the repository
- `dry_run`: If true, no modifications are made to existing tickets. If false, the described modifications are made
