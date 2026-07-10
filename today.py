"""
Daily README stats updater, adapted from Andrew6rant/Andrew6rant (today.py).

Queries the GitHub GraphQL API for live profile stats and rewrites the
id-tagged elements in dark_mode.svg / light_mode.svg. Run by
.github/workflows/build.yaml every day.

Required env vars:
    ACCESS_TOKEN  - GitHub token with read access to repos/profile
    USER_NAME     - GitHub username (defaults to abd-ulbasit)
"""
import datetime
import hashlib
import os
import time

import requests
from dateutil import relativedelta
from lxml import etree

HEADERS = {'authorization': 'token ' + os.environ['ACCESS_TOKEN']}
USER_NAME = os.environ.get('USER_NAME', 'abd-ulbasit')
BIRTHDAY = datetime.datetime(2003, 9, 8)
QUERY_COUNT = {'user_getter': 0, 'follower_getter': 0, 'graph_repos_stars': 0, 'recursive_loc': 0, 'graph_commits': 0, 'loc_query': 0}
CACHE_COMMENT_SIZE = 7


def daily_readme(birthday):
    """
    Returns the length of time since birth, e.g. 'XX years, XX months, XX days'
    """
    diff = relativedelta.relativedelta(datetime.datetime.today(), birthday)
    return '{} {}, {} {}, {} {}{}'.format(
        diff.years, 'year' + format_plural(diff.years),
        diff.months, 'month' + format_plural(diff.months),
        diff.days, 'day' + format_plural(diff.days),
        ' 🎂' if (diff.months == 0 and diff.days == 0) else '')


def format_plural(unit):
    return 's' if unit != 1 else ''


def graphql_post(query, variables, retries=4):
    """
    POSTs a GraphQL query, retrying on GitHub's transient 5xx gateway errors.
    """
    for attempt in range(retries):
        request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables': variables}, headers=HEADERS)
        if request.status_code < 500:
            return request
        if attempt < retries - 1:
            time.sleep(2 ** attempt * 5)
    return request


def simple_request(func_name, query, variables):
    """
    Returns a request, or raises an Exception if the response does not succeed.
    """
    request = graphql_post(query, variables)
    if request.status_code == 200:
        return request
    raise Exception(func_name, ' has failed with a', request.status_code, request.text, QUERY_COUNT)


def graph_repos_stars(count_type, owner_affiliation, cursor=None):
    """
    Returns the total repository or star count via the GraphQL API.
    """
    query_count('graph_repos_stars')
    query = '''
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: $owner_affiliation) {
                totalCount
                edges {
                    node {
                        ... on Repository {
                            nameWithOwner
                            stargazers {
                                totalCount
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }'''
    variables = {'owner_affiliation': owner_affiliation, 'login': USER_NAME, 'cursor': cursor}
    request = simple_request(graph_repos_stars.__name__, query, variables)
    if count_type == 'repos':
        return request.json()['data']['user']['repositories']['totalCount']
    elif count_type == 'stars':
        return stars_counter(request.json()['data']['user']['repositories']['edges'])


def recursive_loc(owner, repo_name, data, cache_comment, addition_total=0, deletion_total=0, my_commits=0, cursor=None):
    """
    Fetches commits from a repository page by page, counting LOC authored by me.
    Steps the page size down when GitHub cannot compute the diff stats for a
    full page (it returns 502 on commits with enormous diffs).
    """
    query_count('recursive_loc')
    query = '''
    query ($repo_name: String!, $owner: String!, $cursor: String, $page_size: Int!) {
        repository(name: $repo_name, owner: $owner) {
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: $page_size, after: $cursor) {
                            totalCount
                            edges {
                                node {
                                    ... on Commit {
                                        committedDate
                                    }
                                    author {
                                        user {
                                            id
                                        }
                                    }
                                    deletions
                                    additions
                                }
                            }
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                        }
                    }
                }
            }
        }
    }'''
    for page_size in (100, 25, 5):
        variables = {'repo_name': repo_name, 'owner': owner, 'cursor': cursor, 'page_size': page_size}
        # not simple_request(): the cache file must be saved before raising
        request = graphql_post(query, variables, retries=2)
        if request.status_code == 200:
            if request.json()['data']['repository']['defaultBranchRef'] is not None:  # only count commits if repo isn't empty
                return loc_counter_one_repo(owner, repo_name, data, cache_comment, request.json()['data']['repository']['defaultBranchRef']['target']['history'], addition_total, deletion_total, my_commits)
            else:
                return 0
        if request.status_code != 502:
            break
    force_close_file(data, cache_comment)
    if request.status_code == 403:
        raise Exception("Too many requests in a short amount of time!\nYou've hit the non-documented anti-abuse limit!")
    raise Exception('recursive_loc() has failed with a', request.status_code, request.text, QUERY_COUNT)


def loc_counter_one_repo(owner, repo_name, data, cache_comment, history, addition_total, deletion_total, my_commits):
    """
    Sums LOC of my commits, recursing through pages of 100.
    """
    for node in history['edges']:
        if node['node']['author']['user'] == OWNER_ID:
            my_commits += 1
            addition_total += node['node']['additions']
            deletion_total += node['node']['deletions']

    if history['edges'] == [] or not history['pageInfo']['hasNextPage']:
        return addition_total, deletion_total, my_commits
    else:
        return recursive_loc(owner, repo_name, data, cache_comment, addition_total, deletion_total, my_commits, history['pageInfo']['endCursor'])


def loc_query(owner_affiliation, comment_size=0, force_cache=False, cursor=None, edges=[]):
    """
    Queries all repositories I have access to, 60 at a time.
    """
    query_count('loc_query')
    query = '''
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 60, after: $cursor, ownerAffiliations: $owner_affiliation) {
            edges {
                node {
                    ... on Repository {
                        nameWithOwner
                        defaultBranchRef {
                            target {
                                ... on Commit {
                                    history {
                                        totalCount
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }'''
    variables = {'owner_affiliation': owner_affiliation, 'login': USER_NAME, 'cursor': cursor}
    request = simple_request(loc_query.__name__, query, variables)
    if request.json()['data']['user']['repositories']['pageInfo']['hasNextPage']:
        edges += request.json()['data']['user']['repositories']['edges']
        return loc_query(owner_affiliation, comment_size, force_cache, request.json()['data']['user']['repositories']['pageInfo']['endCursor'], edges)
    else:
        return cache_builder(edges + request.json()['data']['user']['repositories']['edges'], comment_size, force_cache)


def cache_builder(edges, comment_size, force_cache, loc_add=0, loc_del=0):
    """
    Refreshes the LOC cache for repositories whose commit count changed.
    """
    cached = True
    filename = 'cache/' + hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest() + '.txt'
    try:
        with open(filename, 'r') as f:
            data = f.readlines()
    except FileNotFoundError:
        data = []
        if comment_size > 0:
            for _ in range(comment_size):
                data.append('This line is a comment block. Write whatever you want here.\n')
        with open(filename, 'w') as f:
            f.writelines(data)

    if len(data) - comment_size != len(edges) or force_cache:  # repo count changed
        cached = False
        flush_cache(edges, filename, comment_size)
        with open(filename, 'r') as f:
            data = f.readlines()

    cache_comment = data[:comment_size]
    data = data[comment_size:]
    for index in range(len(edges)):
        repo_hash, commit_count, *__ = data[index].split()
        if repo_hash == hashlib.sha256(edges[index]['node']['nameWithOwner'].encode('utf-8')).hexdigest():
            try:
                if int(commit_count) != edges[index]['node']['defaultBranchRef']['target']['history']['totalCount']:
                    owner, repo_name = edges[index]['node']['nameWithOwner'].split('/')
                    loc = recursive_loc(owner, repo_name, data, cache_comment)
                    data[index] = repo_hash + ' ' + str(edges[index]['node']['defaultBranchRef']['target']['history']['totalCount']) + ' ' + str(loc[2]) + ' ' + str(loc[0]) + ' ' + str(loc[1]) + '\n'
            except TypeError:  # empty repo
                data[index] = repo_hash + ' 0 0 0 0\n'
    with open(filename, 'w') as f:
        f.writelines(cache_comment)
        f.writelines(data)
    for line in data:
        loc = line.split()
        loc_add += int(loc[3])
        loc_del += int(loc[4])
    return [loc_add, loc_del, loc_add - loc_del, cached]


def flush_cache(edges, filename, comment_size):
    """
    Wipes the cache file, keeping only the comment block.
    """
    with open(filename, 'r') as f:
        data = []
        if comment_size > 0:
            data = f.readlines()[:comment_size]
    with open(filename, 'w') as f:
        f.writelines(data)
        for node in edges:
            f.write(hashlib.sha256(node['node']['nameWithOwner'].encode('utf-8')).hexdigest() + ' 0 0 0 0\n')


def force_close_file(data, cache_comment):
    """
    Saves partial cache data if the program crashes mid-write.
    """
    filename = 'cache/' + hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest() + '.txt'
    with open(filename, 'w') as f:
        f.writelines(cache_comment)
        f.writelines(data)
    print('There was an error while writing to the cache file. The file,', filename, 'has had the partial data saved and closed.')


def stars_counter(data):
    return sum(node['node']['stargazers']['totalCount'] for node in data)


def svg_overwrite(filename, age_data, commit_data, star_data, repo_data, contrib_data, follower_data, loc_data, pview_data):
    """
    Updates the id-tagged elements of an SVG card with the latest values.
    """
    tree = etree.parse(filename)
    root = tree.getroot()
    if pview_data is not None:
        justify_format(root, 'pview_data', pview_data, 40)
    # each length is the dots+value budget that right-aligns its line to
    # the 58-char column built by scripts/generate_svg.py
    justify_format(root, 'age_data', age_data, 47)
    justify_format(root, 'commit_data', commit_data, 22)
    justify_format(root, 'star_data', star_data, 13)
    justify_format(root, 'repo_data', repo_data, 6)
    justify_format(root, 'contrib_data', contrib_data)
    justify_format(root, 'follower_data', follower_data, 9)
    justify_format(root, 'loc_data', loc_data[2], 13)
    justify_format(root, 'loc_add', loc_data[0])
    justify_format(root, 'loc_del', loc_data[1], 7)
    tree.write(filename, encoding='utf-8', xml_declaration=True)


def justify_format(root, element_id, new_text, length=0):
    """
    Sets element text and resizes the dot leader before it so the line
    stays right-aligned as the value's width changes.
    """
    if isinstance(new_text, int):
        new_text = f"{'{:,}'.format(new_text)}"
    new_text = str(new_text)
    find_and_replace(root, element_id, new_text)
    just_len = max(0, length - len(new_text))
    if just_len <= 2:
        dot_string = {0: '', 1: ' ', 2: '. '}[just_len]
    else:
        dot_string = ' ' + ('.' * just_len) + ' '
    find_and_replace(root, f"{element_id}_dots", dot_string)


def find_and_replace(root, element_id, new_text):
    element = root.find(f".//*[@id='{element_id}']")
    if element is not None:
        element.text = new_text


def commit_counter(comment_size):
    """
    Sums my commits from the LOC cache file.
    """
    total_commits = 0
    filename = 'cache/' + hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest() + '.txt'
    with open(filename, 'r') as f:
        data = f.readlines()
    data = data[comment_size:]
    for line in data:
        total_commits += int(line.split()[2])
    return total_commits


def user_getter(username):
    """
    Returns the account ID and creation time of the user.
    """
    query_count('user_getter')
    query = '''
    query($login: String!){
        user(login: $login) {
            id
            createdAt
        }
    }'''
    variables = {'login': username}
    request = simple_request(user_getter.__name__, query, variables)
    return {'id': request.json()['data']['user']['id']}, request.json()['data']['user']['createdAt']


def follower_getter(username):
    """
    Returns the number of followers of the user.
    """
    query_count('follower_getter')
    query = '''
    query($login: String!){
        user(login: $login) {
            followers {
                totalCount
            }
        }
    }'''
    request = simple_request(follower_getter.__name__, query, {'login': username})
    return int(request.json()['data']['user']['followers']['totalCount'])


def profile_views_getter(username):
    """
    Parses the current view count out of the komarev badge SVG. The README
    embeds the invisible style=pixel variant, which does the actual counting;
    this fetch adds one view per day, which is negligible.
    Returns None on failure so a komarev outage doesn't fail the whole run.
    """
    import re
    try:
        resp = requests.get(f'https://komarev.com/ghpvc/?username={username}', timeout=30)
        resp.raise_for_status()
        counts = re.findall(r'>([\d,]+)</text>', resp.text)
        return int(counts[-1].replace(',', ''))
    except Exception as exc:
        print('profile views fetch failed, keeping previous value:', exc)
        return None


def query_count(funct_id):
    global QUERY_COUNT
    QUERY_COUNT[funct_id] += 1


def perf_counter(funct, *args):
    start = time.perf_counter()
    funct_return = funct(*args)
    return funct_return, time.perf_counter() - start


def formatter(query_type, difference):
    print('{:<23}'.format('   ' + query_type + ':'), sep='', end='')
    print('{:>12}'.format('%.4f' % difference + ' s ')) if difference > 1 else print('{:>12}'.format('%.4f' % (difference * 1000) + ' ms'))


if __name__ == '__main__':
    print('Calculation times:')
    user_data, user_time = perf_counter(user_getter, USER_NAME)
    OWNER_ID, acc_date = user_data
    formatter('account data', user_time)
    age_data, age_time = perf_counter(daily_readme, BIRTHDAY)
    formatter('age calculation', age_time)
    total_loc, loc_time = perf_counter(loc_query, ['OWNER', 'COLLABORATOR', 'ORGANIZATION_MEMBER'], CACHE_COMMENT_SIZE)
    formatter('LOC (cached)', loc_time) if total_loc[-1] else formatter('LOC (no cache)', loc_time)
    commit_data, commit_time = perf_counter(commit_counter, CACHE_COMMENT_SIZE)
    formatter('commit counter', commit_time)
    star_data, star_time = perf_counter(graph_repos_stars, 'stars', ['OWNER'])
    formatter('star counter', star_time)
    repo_data, repo_time = perf_counter(graph_repos_stars, 'repos', ['OWNER'])
    formatter('repo counter', repo_time)
    contrib_data, contrib_time = perf_counter(graph_repos_stars, 'repos', ['OWNER', 'COLLABORATOR', 'ORGANIZATION_MEMBER'])
    formatter('contrib counter', contrib_time)
    follower_data, follower_time = perf_counter(follower_getter, USER_NAME)
    formatter('follower counter', follower_time)
    pview_data, pview_time = perf_counter(profile_views_getter, USER_NAME)
    formatter('profile views', pview_time)

    for index in range(len(total_loc) - 1):
        total_loc[index] = '{:,}'.format(total_loc[index])  # format added, deleted, and total LOC

    svg_overwrite('dark_mode.svg', age_data, commit_data, star_data, repo_data, contrib_data, follower_data, total_loc[:-1], pview_data)
    svg_overwrite('light_mode.svg', age_data, commit_data, star_data, repo_data, contrib_data, follower_data, total_loc[:-1], pview_data)

    print('Total GitHub GraphQL API calls:', '{:>3}'.format(sum(QUERY_COUNT.values())))
    for funct_name, count in QUERY_COUNT.items():
        print('{:<28}'.format('   ' + funct_name + ':'), '{:>6}'.format(count))
