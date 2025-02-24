import json
import os
import os.path

import requests

# DON'T MODIFY THESE UNLESS YOU SET INIT_FROM_FILE TO FALSE (NOT RECOMMENDED)
TOKEN = ''
OWNER = ''
REPO = ''

DRY_RUN = True

INIT_FROM_FILE = True

if INIT_FROM_FILE:
    if not os.path.isfile('config.json'):

        with open('config.json', 'a') as f:
            f.write(json.dumps({'token': '', 'owner': '', 'repo': '',
                    'dry_run': False}, ensure_ascii=False, indent=4))
        raise Exception(
            "config.json created - please fill and restart the script.")
    else:
        with open('config.json') as f:
            d = json.load(f)
            TOKEN = d['token']
            OWNER = d['owner']
            REPO = d['repo']
            DRY_RUN = d['dry_run']


HEADERS = {'User-Agent': 'github-issues-fixer/1.0',
           'Authorization': 'bearer {0}'.format(TOKEN)}

LISTITEM_START_TODO = '- [ ] '
LISTITEM_START_DONE = '- [x] '


def main():
    issues = list(get_issues(OWNER, REPO))
    print(f'Found {len(issues)} issues')

    filtercritera = r'```[tasklist]'
    filtered_list = filter_issues(issues, filtercritera)

    print(
        f'Found {len(filtered_list)} issues with filter criteria "{filtercritera}"')

    # Use this if you want to limit/filter the processed issues
    # filtered_list = [filtered_list[0]] # only process the newest issue

    updated_issues = process(
        filtered_list, '```[tasklist]\n', '\n```', 'body', replace_childlinks=True)

    print(f'Updated {len(updated_issues)} issues')


def process(issue_list, replace_start, replace_end, replacefield='body', replace_childlinks=False):

    for issue in issue_list:
        fieldval = issue[replacefield]
        if fieldval is None:
            continue

        # find tag to replace
        while (start_index := fieldval.find(replace_start)) != -1:
            stop_index = fieldval.find(
                replace_end, start_index+len(replace_start))
            if (stop_index == -1):
                continue

            print(f'Found {replace_start} in issue #{issue['number']}')
            before = fieldval[:start_index]
            between = fieldval[start_index+len(replace_start):stop_index]

            if (replace_childlinks):
                replaced_between, sub_issues = findandreplace_potential_subissues(
                    between)
                if sub_issues is not None and len(sub_issues) != 0:
                    add_subissues(issue['number'], sub_issues)
                    between = replaced_between

            after = fieldval[stop_index+len(replace_end):]

            fieldval = before + between + after

            issue[replacefield] = fieldval

        update_issue(issue)
    return issue_list


def update_issue(issuejson, replacefield='body'):
    issue_number = issuejson['number']
    req_url = f'https://api.github.com/repos/{OWNER}/{REPO}/issues/{issue_number}'

    req_data = {replacefield: issuejson[replacefield]}
    print(f'Patching issue {issue_number} with req_data: {req_data}')

    if not DRY_RUN:
        r = requests.patch(req_url,
                           data=json.dumps(req_data),
                           headers=HEADERS)
        if r.status_code != 200:
            raise Exception("HTTP status {0} on patching issue {1}'s field \"{2}\" with params {3}".format(
                r.status_code, id,
                issue_number, replacefield, req_data))


def findandreplace_potential_subissues(content):
    # assume they're in split lines
    lines = content.split('\n')
    subissue_ids = []

    for line in lines:
        line = line.strip()
        id = None
        if (line.startswith(LISTITEM_START_TODO)):
            id = get_issueid(line, LISTITEM_START_TODO)
        elif (line.startswith(LISTITEM_START_DONE)):
            id = get_issueid(line, LISTITEM_START_DONE)

        if id is not None:
            # remove todolist item since it's going to be a subissue
            content = content.replace(line, '')
            subissue_ids.append(id)

    return content, subissue_ids


def add_subissues(parentissue_number, subissue_ids):

    issues_url = f'https://api.github.com/repos/{OWNER}/{REPO}/issues/{parentissue_number}'
    req_url = issues_url+'/sub_issues'
    for id in subissue_ids:
        req_data = {'sub_issue_id': id, 'replace_parent': True}
        print(f'Adding subissue {id} to {parentissue_number}')
        if not DRY_RUN:
            r = requests.post(req_url,
                              data=json.dumps(req_data),
                              headers=HEADERS)

            if r.status_code == 422 and r.text.find("Issue may not contain duplicate sub-issues") != -1:
                print(f"Ignoring duplicate subissue {id}")
                continue

            if r.status_code != 201:
                raise Exception("HTTP status {0} on adding subissue {1} to {2}".format(
                    r.status_code, id,
                    issues_url))


def get_issueid(line, linestart):
    line = line[len(linestart):].strip()
    if (line.startswith('#')):
        line = line[line.index('#')+1:]
        if (line.isdecimal()):
            return get_issueid_fromapi(OWNER, REPO, int(line))
        else:
            print(
                f"Ignoring todo item {line} due to bad format (non-int issue number). Treating as text!")
            return None
    elif line.startswith("https://github.com/"):
        # extract owner, repo, number
        pathparts = line.split('/')
        issueowner = pathparts[3]
        issuerepo = pathparts[4]
        issuenumber = pathparts[6]

        if (issuenumber.isdecimal()):
            return get_issueid_fromapi(issueowner, issuerepo, int(issuenumber))
        else:
            print(
                f"Ignoring todo item {line} due to bad format (non-int issue number). Treating as text!")
            return None
    else:
        return None


def get_issueid_fromapi(issueowner, issuerepo, issuenumber):
    issues_url = f'https://api.github.com/repos/{issueowner}/{issuerepo}/issues/{issuenumber}'
    r = requests.get(issues_url,
                     params={},
                     headers=HEADERS)

    if r.status_code == 404:
        print(
            f'Potential subissue {issues_url} not found. Treating as normal item, not as subissue')
        return None
    if r.status_code != 200:
        raise Exception("HTTP status {0} on fetching {1}".format(
            r.status_code,
            issues_url))

    issues_json = r.json()
    return issues_json['id']


def filter_issues(issue_list, searchstring,  searchfield='body'):
    filtered_list = []
    for issue in issue_list:
        body = issue[searchfield]
        if body is None:
            continue
        if searchstring in body:  # Use regex.match for matching from the beginning of the string
            filtered_list.append(issue)

    return filtered_list


def get_issues(owner, repo, state='all'):
    page = 1
    while True:
        issues_url = f'https://api.github.com/repos/{owner}/{repo}/issues'
        r = requests.get(issues_url,
                         params={'per_page': '100',
                                 'page': str(page),
                                 'state': state},
                         headers=HEADERS)
        if r.status_code != 200:
            raise Exception("HTTP status {0} on fetching {1}".format(
                r.status_code,
                issues_url))

        issues_json = r.json()
        for issue in issues_json:
            yield issue

        page += 1
        if 'Link' not in r.headers:
            break
        if 'rel="next"' not in r.headers['Link']:
            break


if __name__ == "__main__":
    main()
