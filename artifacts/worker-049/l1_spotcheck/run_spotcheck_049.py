#!/usr/bin/env python3
"""Independent L1 re-fetch spot check #5 at ledger/citation_audit.csv sha256 315c19145065.

worker-049, node L1, gate G-LIT, class bindings via each row's class_mapping.
Design:
  * sample frozen in sample_freeze.json BEFORE any network call (rows never re-fetched at this sha);
  * raw response body saved and sha256'd on receipt (never re-typed);
  * bodies fetched earlier in this same task are byte-identical cache reuse (recorded per row);
  * ledger re-hashed after the fetch loop; abort/flag on drift;
  * comparison is mechanical (math-aware title tokens, excerpt token coverage, year/authors) and the
    reading is recorded separately so the verdict can be audited; a journal-DOI secondary fetch
    resolves arXiv-v1-year vs published-year conventions.
stdlib only; primary APIs (arXiv, Crossref, INSPIRE, OpenAlex); no ledger text is used as evidence.
"""
import csv, datetime, difflib, hashlib, html, json, os, re, sys, time, unicodedata
import urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUTDIR = os.path.join(ROOT, 'artifacts', 'worker-049', 'l1_spotcheck')
RAWDIR = os.path.join(OUTDIR, 'raw')
LEDGER = os.path.join(ROOT, 'ledger', 'citation_audit.csv')
FETCH_LOG = os.path.join(OUTDIR, 'fetch_log.tsv')
PINNED = '315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9'
SLEEP = 4.0
TIMEOUT = 45
UA = 'worker-049-l1-spotcheck/1.0 (research ledger verification)'
# declared before this fetch: used only where the ledger has no DOI and the venue year is 'per secondary citation'
TARGETED_SEARCH = {
    'SRC-066': 'https://api.openalex.org/works?filter=title.search:Instability%20results%20for%20the%20wave%20equation%20in%20the%20interior%20of%20Kerr%20black%20holes&per-page=3',
}


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def norm(s):
    s = unicodedata.normalize('NFKC', s or '')
    for a, b in (('\u2013', '-'), ('\u2014', '-'), ('\u2019', "'"), ('\u201c', '"'), ('\u201d', '"')):
        s = s.replace(a, b)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))  # Nordstroem -> Nordstrom for token compare
    return re.sub(r'\s+', ' ', s).strip().lower()


def detex_umlaut(s):
    table = {'a': '\u00e4', 'o': '\u00f6', 'u': '\u00fc', 'A': '\u00c4', 'O': '\u00d6', 'U': '\u00dc'}
    return re.sub(r'\\"([aouAOU])', lambda m: table[m.group(1)], s or '')


def strip_latex(s):
    s = s or ''
    s = re.sub(r'\$+', ' ', s)
    s = re.sub(r'\\[a-zA-Z]+', ' ', s)
    return s.replace('{', ' ').replace('}', ' ').replace('^', ' ').replace('_', ' ')


def tokens(s):
    return re.findall(r'[a-z0-9]+', norm(strip_latex(s)))


def strip_quote_prefix(q):
    q = (q or '').strip()
    q = re.sub(r'^[A-Za-z0-9 ,\.\(\)/\-\^\[\]]{0,80}?:\s*', '', q, count=1)
    q = q.strip('"\u201c\u201d\' ')
    q = re.sub(r'^(\.\.\.|\u2026)+\s*', '', q)
    q = re.sub(r'\s*(\.\.\.|\u2026)+$', '', q)
    return q.strip()


ADDENDUM_RE = re.compile(r'\b(journal reference on page|journal reference|journal ref|per secondary citation|related doi)\b', re.I)


def split_addendum(quote):
    q = quote or ''
    m = ADDENDUM_RE.search(q)
    if not m:
        return q, ''
    return q[:m.start()].strip(' .;:'), q[m.start():].strip()


def clean_title(t):
    t = t or ''
    return re.sub(r'\s*\((arXiv version with journal ref|Crossref record|INSPIRE record|published version)\)\s*$', '', t, flags=re.I).strip()


def surname_set(authors):
    out = set()
    for a in re.split(r';|,| and ', authors or ''):
        a = norm(a)
        if a:
            parts = a.split()
            if parts:
                out.add(parts[-1])
    return out


def token_coverage(quote, text):
    lt, ft = tokens(quote), tokens(text)
    if not lt or not ft:
        return None, None
    rem = Counter(ft)
    common = 0
    for tk in lt:
        if rem[tk] > 0:
            common += 1
            rem[tk] -= 1
    ordered = round(difflib.SequenceMatcher(None, lt, ft).ratio(), 4)
    return round(common / len(lt), 4), ordered


# ---------- fetch with live/cache distinction ----------

def live_fetch(url):
    last = None
    for attempt, backoff in enumerate((0, 8, 20, 40), start=1):
        if backoff:
            time.sleep(backoff)
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return {'http_status': r.status, 'body': r.read(), 'final_url': r.geturl(),
                        'attempt': attempt, 'error': ''}
        except urllib.error.HTTPError as e:
            last = {'http_status': e.code, 'body': b'', 'final_url': url, 'attempt': attempt, 'error': f'HTTPError {e.code}'}
        except Exception as e:  # noqa: BLE001
            last = {'http_status': None, 'body': b'', 'final_url': url, 'attempt': attempt, 'error': f'{type(e).__name__}: {e}'}
    return last


def get_body(url, raw_name, prior_log):
    raw_path = os.path.join(RAWDIR, raw_name)
    prior = prior_log.get(raw_name, {})
    if os.path.exists(raw_path) and os.path.getsize(raw_path) == 0 and prior.get('http_status') in (None, '', '200'):
        return {'http_status': int(prior['http_status']) if prior.get('http_status') not in (None, '') else None,
                'body': b'', 'final_url': url, 'attempt': prior.get('attempts', 1),
                'error': 'cached empty body (recorded failure)', 'cache_reused': True,
                'fetched_at': prior.get('fetched_at', now()), 'raw_sha256': sha256_bytes(b'')}
    if os.path.exists(raw_path) and os.path.getsize(raw_path) > 0:
        body = open(raw_path, 'rb').read()
        ts = prior.get('fetched_at') or datetime.datetime.fromtimestamp(os.path.getmtime(raw_path)).astimezone().isoformat(timespec='seconds')
        return {'http_status': 200, 'body': body, 'final_url': url, 'attempt': prior.get('attempts', 1),
                'error': '', 'cache_reused': True, 'fetched_at': ts,
                'raw_sha256': sha256_bytes(body)}
    if os.path.exists(raw_path) and prior.get('http_status') not in (None, '', '200'):
        # cached failure: the recorded 429 (or other error) is itself evidence; do not re-hammer the API
        return {'http_status': int(prior['http_status']), 'body': b'', 'final_url': url,
                'attempt': prior.get('attempts', 1), 'error': f"cached HTTPError {prior['http_status']}",
                'cache_reused': True, 'fetched_at': prior.get('fetched_at', now()), 'raw_sha256': sha256_bytes(b'')}
    f = live_fetch(url)
    body = f['body']
    with open(raw_path, 'wb') as fh:
        fh.write(body)
    time.sleep(SLEEP)
    return {**f, 'cache_reused': False, 'fetched_at': now(), 'raw_sha256': sha256_bytes(body)}


# ---------- parsers ----------

def parse_arxiv(body):
    root = ET.fromstring(body)
    ns = {'a': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
    entry = root.find('a:entry', ns)
    if entry is None:
        return {'kind': 'arxiv_api', 'error': 'no entry'}
    title = re.sub(r'\s+', ' ', (entry.findtext('a:title', '', ns) or '')).strip()
    abstract = re.sub(r'\s+', ' ', (entry.findtext('a:summary', '', ns) or '')).strip()
    authors = '; '.join((a.findtext('a:name', '', ns) or '').strip() for a in entry.findall('a:author', ns))
    published = (entry.findtext('a:published', '', ns) or '')[:10]
    updated = (entry.findtext('a:updated', '', ns) or '')[:10]
    return {'kind': 'arxiv_api', 'title': title, 'abstract': abstract, 'authors': authors,
            'published': published, 'updated': updated,
            'journal_ref': (entry.findtext('arxiv:journal_ref', '', ns) or '').strip(),
            'doi': (entry.findtext('arxiv:doi', '', ns) or '').strip(), 'year': published[:4]}


def _jats_text(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or '')).strip()


def parse_crossref(body):
    d = json.loads(body.decode('utf-8', 'replace'))['message']
    issued = (d.get('issued', {}).get('date-parts') or [[None]])[0]
    return {'kind': 'crossref_api', 'title': (d.get('title') or [''])[0],
            'authors': '; '.join(f"{a.get('given','')} {a.get('family','')}".strip() for a in d.get('author', [])),
            'year': str(issued[0]) if issued and issued[0] else '',
            'container_title': (d.get('container-title') or [''])[0], 'volume': d.get('volume', ''),
            'issue': d.get('issue', ''), 'page': d.get('page', ''), 'doi': d.get('DOI', ''),
            'abstract': _jats_text(d.get('abstract', ''))}


def parse_inspire(body):
    d = json.loads(body.decode('utf-8', 'replace'))
    md = (d.get('metadata') or {})
    abstract = next((ab['value'] for ab in md.get('abstracts', []) if ab.get('value')), '')
    doi = next((di['value'] for di in md.get('dois', []) if di.get('value')), '')
    ji = (md.get('publication_info') or [{}])[0]
    return {'kind': 'inspire_api', 'title': (md.get('titles') or [{}])[0].get('title', ''),
            'authors': '; '.join(a.get('full_name', '') for a in md.get('authors', [])),
            'year': str(ji.get('year', '') or (md.get('preprint_date', '') or '')[:4]), 'doi': doi,
            'abstract': abstract, 'journal_title': ji.get('journal_title', ''),
            'journal_volume': ji.get('journal_volume', ''), 'page_start': ji.get('page_start', '')}


def parse_openalex(body):
    d = json.loads(body.decode('utf-8', 'replace'))
    pos = {i: tok for tok, idxs in (d.get('abstract_inverted_index') or {}).items() for i in idxs}
    return {'kind': 'openalex_api', 'title': d.get('title', ''),
            'abstract': ' '.join(pos[i] for i in sorted(pos)),
            'authors': '; '.join(a.get('author', {}).get('display_name', '') for a in d.get('authorships', [])),
            'year': str(d.get('publication_year', '')), 'doi': d.get('doi', '')}


def parse_html(body):
    txt = html.unescape(body.decode('utf-8', 'replace'))
    meta = {}
    for name in ('citation_title', 'citation_author', 'citation_publication_date', 'citation_journal_title', 'citation_doi'):
        mm = re.search(r'<meta[^>]+name=["\']%s["\'][^>]+content=["\'](.*?)["\']' % name, txt, re.S | re.I)
        if mm:
            meta[name] = re.sub(r'\s+', ' ', mm.group(1)).strip()
    m = re.search(r'<title[^>]*>(.*?)</title>', txt, re.S | re.I)
    title = re.sub(r'\s+', ' ', m.group(1)).strip() if m else ''
    ab = re.search(r'<blockquote[^>]*class=["\'][^"\']*abstract[^"\']*["\'][^>]*>(.*?)</blockquote>', txt, re.S | re.I)
    abstract = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', ab.group(1))).strip() if ab else ''
    if not abstract:
        plain = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', txt, flags=re.S | re.I)
        abstract = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', plain))
    return {'kind': 'html_page', 'title': detex_umlaut(meta.get('citation_title') or title),
            'authors': meta.get('citation_author', ''), 'year': (meta.get('citation_publication_date', '') or '')[:4],
            'journal_title': meta.get('citation_journal_title', ''), 'doi': meta.get('citation_doi', ''),
            'abstract': detex_umlaut(abstract)}


PARSERS = {'arxiv_api': parse_arxiv, 'crossref_api': parse_crossref, 'inspire_api': parse_inspire,
           'openalex_api': parse_openalex, 'html_page': parse_html}


def parse(kind, body):
    try:
        return PARSERS[kind](body)
    except Exception as e:  # noqa: BLE001
        return {'kind': kind, 'error': f'{type(e).__name__}: {e}'}


def choose_locator(row):
    aid, doi = (row.get('arxiv_id') or '').strip(), (row.get('doi') or '').strip()
    ev, loc = (row.get('evidence_url') or '').strip(), (row.get('exact_locator') or '').strip()
    if aid:
        return f'https://export.arxiv.org/api/query?id_list={urllib.parse.quote(aid, safe="")}', 'arxiv_api', 'arxiv_id_field'
    if doi:
        return f'https://api.crossref.org/works/{urllib.parse.quote(doi, safe="")}', 'crossref_api', 'doi_field'
    if 'inspirehep.net/api/literature/' in ev:
        return ev, 'inspire_api', 'evidence_url_record'
    if 'openalex.org' in ev:
        return ev, 'openalex_api', 'evidence_url_record'
    if ev.startswith('http'):
        return ev, 'html_page', 'evidence_url'
    return loc or ev, 'html_page', 'exact_locator_search'


def is_search_locator(row):
    s = ((row.get('exact_locator') or '') + ' ' + (row.get('evidence_url') or '')).lower()
    return ('search_query' in s) or ('/api/literature?q=' in s) or ('?' in s and 'api/literature/' not in s)


def main():
    ledger_sha_before = sha256_file(LEDGER)
    before_nonempty = {}
    if os.path.exists(FETCH_LOG):
        log_lines = [l.rstrip('\n').split('\t') for l in open(FETCH_LOG) if l.strip()]
        hdr = {name: i for i, name in enumerate(log_lines[0])}
        for parts in log_lines[1:]:
            if 'raw_file' in hdr and len(parts) > hdr['raw_file']:
                before_nonempty[parts[hdr['raw_file']]] = {
                    'fetched_at': parts[hdr['fetched_at']], 'http_status': parts[hdr['http_status']],
                    'attempts': parts[hdr.get('attempts', 0)], 'locator_used': parts[hdr.get('locator_used', 0)]}
    freeze = json.load(open(os.path.join(OUTDIR, 'sample_freeze.json')))
    rows = {r['citation_id']: r for r in csv.DictReader(open(LEDGER, newline=''))}
    sample_ids = freeze['sample_ids']

    if ledger_sha_before != PINNED:
        blocker = {'schema_version': '0.1', 'artifact_type': 'l1_spotcheck_blocker', 'node_id': 'L1', 'gate': 'G-LIT',
                   'actor': 'worker-049', 'created_at': now(),
                   'reason': 'moving target: ledger/citation_audit.csv no longer at pinned sha256 315c19145065',
                   'measured_before': ledger_sha_before, 'pinned': PINNED, 'action': 'fail-closed abort before fetching'}
        json.dump(blocker, open(os.path.join(OUTDIR, 'spotcheck-l1-049.blocker.json'), 'w'), indent=1)
        print('ABORT: ledger drifted', ledger_sha_before)
        return 2

    os.makedirs(RAWDIR, exist_ok=True)
    fetch_log, results = [], []

    def log_fetch(cid, role, url, kind, f, raw_name, raw_path):
        rec = {'fetched_at': f['fetched_at'], 'citation_id': cid, 'role': role, 'http_status': f['http_status'],
               'bytes': len(f['body']), 'raw_file': os.path.relpath(raw_path, ROOT), 'raw_sha256': f['raw_sha256'],
               'locator_used': url, 'locator_kind': kind, 'attempts': f.get('attempt', 1),
               'cache_reused': f.get('cache_reused', False), 'error': f.get('error', '')}
        fetch_log.append(rec)
        return rec

    def write_log():
        with open(FETCH_LOG, 'w') as fh:
            fh.write('\t'.join(['fetched_at', 'citation_id', 'role', 'http_status', 'bytes', 'raw_file',
                                'raw_sha256', 'locator_used', 'locator_kind', 'attempts', 'cache_reused', 'error']) + '\n')
            for e in fetch_log:
                fh.write('\t'.join(str(e.get(k, '')) for k in ('fetched_at', 'citation_id', 'role', 'http_status', 'bytes',
                                                               'raw_file', 'raw_sha256', 'locator_used', 'locator_kind',
                                                               'attempts', 'cache_reused', 'error')) + '\n')

    for cid in sample_ids:
        row = rows[cid]
        url, kind, my_quality = choose_locator(row)
        raw_name = f"row{int(cid.split('-')[1]):03d}_{cid}_{kind}.body"
        raw_path = os.path.join(RAWDIR, raw_name)
        f = get_body(url, raw_name, before_nonempty)
        primary = parse(kind, f['body']) if f['body'] else {'kind': kind, 'error': f.get('error') or 'empty body'}
        used_kind, used_url, fallback = kind, url, ''
        if (f['http_status'] != 200 or not f['body']) and row.get('arxiv_id'):
            # record the failed locator attempt, then fall back to the primary landing page (abs page)
            log_fetch(cid, 'primary_failed', used_url, used_kind, f, raw_name, raw_path)
            write_log()
            used_kind = 'html_page'
            used_url = f"https://arxiv.org/abs/{urllib.parse.quote(row['arxiv_id'], safe='')}"
            raw_name = f"row{int(cid.split('-')[1]):03d}_{cid}_arxiv_abs_page.body"
            raw_path = os.path.join(RAWDIR, raw_name)
            f2 = get_body(used_url, raw_name, before_nonempty)
            fallback = f"arxiv_api_{f.get('error') or f['http_status']} -> abs_page"
            if f2['body']:
                f, primary = f2, parse('html_page', f2['body'])
        rec = log_fetch(cid, 'primary_fallback_abs_page' if fallback else 'primary', used_url, used_kind, f, raw_name, raw_path)
        write_log()
        print(f"{cid} primary {f['http_status']} {len(f['body'])}B {raw_name}{' (cache)' if f.get('cache_reused') else ''}")
        # secondary: journal DOI via Crossref when the ledger carries one (skip arXiv/DataCite DOIs)
        doi = (row.get('doi') or '').strip()
        secondary, sec_rec = None, None
        if doi and not doi.lower().startswith('10.48550/arxiv'):
            surl = f'https://api.crossref.org/works/{urllib.parse.quote(doi, safe="")}'
            sname = f"row{int(cid.split('-')[1]):03d}_{cid}_crossref_secondary.body"
            spath = os.path.join(RAWDIR, sname)
            sf = get_body(surl, sname, before_nonempty)
            sec_rec = log_fetch(cid, 'secondary_crossref', surl, 'crossref_api', sf, sname, spath)
            write_log()
            if sf['body'] and sf['http_status'] == 200:
                secondary = parse('crossref_api', sf['body'])
            print(f"  secondary {sf['http_status']} {len(sf['body'])}B {sname}{' (cache)' if sf.get('cache_reused') else ''}")

        # ---- targeted title-search resolution (declared before fetch; only where the ledger has no DOI) ----
        targeted = None
        if cid in TARGETED_SEARCH and not doi:
            turl = TARGETED_SEARCH[cid]
            tname = f"row{int(cid.split('-')[1]):03d}_{cid}_openalex_title_search.body"
            tpath = os.path.join(RAWDIR, tname)
            tf = get_body(turl, tname, before_nonempty)
            log_fetch(cid, 'targeted_title_search', turl, 'openalex_search', tf, tname, tpath)
            write_log()
            print(f"  targeted search {tf['http_status']} {len(tf['body'])}B {tname}")
            if tf['body'] and tf['http_status'] == 200:
                try:
                    td = json.loads(tf['body'].decode('utf-8', 'replace'))
                    exact = [w for w in td.get('results', []) if tokens(w.get('display_name', '')) == tokens(clean_title(row['title']))]
                    if exact:
                        w = exact[0]
                        src = ((w.get('primary_location') or {}).get('source') or {})
                        targeted = {'kind': 'openalex_title_search', 'matched_title': w.get('display_name', ''),
                                    'year': str(w.get('publication_year', '') or ''),
                                    'doi': (w.get('doi') or '').replace('https://doi.org/', ''),
                                    'venue': src.get('display_name', ''), 'raw_sha256': tf['raw_sha256'],
                                    'raw_file': os.path.relpath(tpath, ROOT)}
                        print(f"    matched: {targeted['venue']} {targeted['year']} doi={targeted['doi']}")
                except Exception as e:  # noqa: BLE001
                    targeted = {'kind': 'openalex_title_search', 'error': f'{type(e).__name__}: {e}'}

        # ---- comparison ----
        meta, meta_source = primary, 'primary_locator_record'
        if secondary and fallback and doi:
            meta, meta_source = secondary, 'secondary_crossref_promoted_over_rate_limited_arxiv_api'
        ltitle = clean_title(row['title'])
        ltoks, ftoks_t = tokens(ltitle), tokens(meta.get('title', ''))
        title_exact = bool(ltoks) and ltoks == ftoks_t
        title_contains = bool(ltoks) and bool(ftoks_t) and (
            ltoks in [ftoks_t[i:i + len(ltoks)] for i in range(max(1, len(ftoks_t) - len(ltoks) + 1))]
            or ftoks_t in [ltoks[i:i + len(ftoks_t)] for i in range(max(1, len(ltoks) - len(ftoks_t) + 1))])
        fy, ly = meta.get('year', '') or '', (row['year'] or '').strip()
        sy = (secondary or {}).get('year', '') if secondary else ''
        ty = (targeted or {}).get('year', '') if targeted else ''
        if fy and fy == ly:
            year_source = 'secondary_crossref_promoted' if meta_source.startswith('secondary') else 'primary_locator_record'
        elif sy and sy == ly:
            year_source = 'secondary_crossref'
        elif ty and ty == ly:
            year_source = 'targeted_openalex_title_search'
        else:
            year_source = 'unresolved'
        year_ok = bool(ly) and year_source != 'unresolved'
        la, fa = surname_set(row['authors']), surname_set(meta.get('authors', ''))
        authors_overlap = (len(la & fa) / len(la)) if la else None
        quote_core, quote_addendum = split_addendum(strip_quote_prefix(row['evidence_excerpt'] or row['elided_quote'] or ''))
        abstract = primary.get('abstract', '') or ((secondary or {}).get('abstract', '') or '')
        coverage, ordered = token_coverage(quote_core, abstract)
        metadata_only = row.get('evidence_type') == 'metadata'
        loc_note = 'ledger exact_locator is a search query; evidence_url/arxiv_id/doi provides a record-level anchor' if is_search_locator(row) else ''

        if not (title_exact or title_contains):
            verdict = 'MISMATCH'
            reading = f"fetched title does not match cited title: fetched={meta.get('title')!r}"
        elif metadata_only:
            verdict = 'MATCH' if year_ok else 'PARTIAL'
            reading = f"metadata record matches title/authors; year {'confirmed' if year_ok else 'differs'} (ledger {ly}, records {fy}/{sy or 'n/a'}/{ty or 'n/a'})"
        elif coverage is None:
            verdict = 'PARTIAL'
            reading = f"title/authors match and year {ly} confirmed via {year_source}, but the cited excerpt could not be re-checked: no abstract in the fetched record(s)"
        elif coverage >= 0.9 and year_ok:
            verdict, reading = 'MATCH', f"excerpt is a verbatim fragment/composite of the fetched abstract (core coverage {coverage}); year confirmed via {year_source}"
        elif coverage >= 0.9 and not year_ok:
            verdict = 'PARTIAL'
            reading = f"excerpt covered (coverage {coverage}) but ledger year {ly} not confirmed by any fetched record (arXiv {fy}, crossref {sy or 'n/a'}, search {ty or 'n/a'})"
        elif coverage >= 0.5:
            verdict = 'PARTIAL'
            reading = f"excerpt token coverage {coverage}; year ledger {ly} via {year_source}"
        else:
            verdict = 'MISMATCH'
            reading = f"cited excerpt not supported by fetched abstract (core coverage {coverage})"
        if quote_addendum:
            reading += f"; ledger excerpt carries a labelled addendum not tested against the source: {quote_addendum[:120]!r}"
        if loc_note and verdict == 'MATCH':
            reading += '; locator-quality note: ' + loc_note
        if fallback:
            reading += f"; primary fallback: {fallback}"
        if targeted and targeted.get('doi') and verdict == 'MATCH':
            reading += f"; targeted title search resolved the record-level DOI {targeted['doi']} ({targeted.get('venue','')} {ty}), which the ledger lacks"

        results.append({
            'row': int(cid.split('-')[1]), 'citation_id': cid, 'bibkey': row['bibkey'],
            'class_mapping': row['class_mapping'], 'used_by_theorems': row['used_by_theorems'],
            'ledger': {'title': row['title'], 'authors': row['authors'], 'year': row['year'], 'venue': row['venue'],
                       'doi': row['doi'], 'arxiv_id': row['arxiv_id'], 'status': row['status'],
                       'verification_method': row['verification_method'], 'evidence_type': row['evidence_type'],
                       'exact_locator': row['exact_locator'], 'evidence_url': row['evidence_url'],
                       'verdict': row['verdict'], 'reviewer': row['reviewer']},
            'locator_used': used_url, 'locator_kind': used_kind, 'primary_locator': url, 'primary_locator_kind': kind,
            'primary_fallback': fallback, 'locator_quality_note': loc_note,
            'metadata_record_used': meta_source, 'metadata_record_sha256': (sec_rec or {}).get('raw_sha256') if meta_source.startswith('secondary') else f['raw_sha256'],
            'targeted_title_search': targeted,
            'fetched_at': f['fetched_at'], 'raw_file': os.path.relpath(raw_path, ROOT), 'raw_sha256': f['raw_sha256'],
            'cache_reused': f.get('cache_reused', False), 'fetch': {'http_status': f['http_status'], 'bytes': len(f['body'])},
            'fetched': {k: primary.get(k) for k in ('kind', 'title', 'authors', 'year', 'doi', 'journal_ref',
                                                    'container_title', 'volume', 'issue', 'page', 'journal_title',
                                                    'published', 'updated', 'error') if primary.get(k) is not None},
            'secondary_crossref': ({k: secondary.get(k) for k in ('kind', 'title', 'authors', 'year', 'doi',
                                                                  'container_title', 'volume', 'issue', 'page')} if secondary else None),
            'secondary_raw_sha256': (sec_rec or {}).get('raw_sha256'),
            'fetched_abstract_excerpt': abstract[:1200],
            'comparison': {'title_token_match': title_exact, 'title_token_contains': title_contains,
                           'ledger_title_tokens': ltoks[:20], 'fetched_title_tokens': ftoks_t[:20],
                           'ledger_year': ly, 'fetched_year': fy, 'secondary_year': sy, 'targeted_year': ty,
                           'year_source': year_source, 'year_ok': year_ok, 'author_surname_overlap': authors_overlap,
                           'excerpt_core_token_coverage': coverage, 'ordered_token_ratio': ordered,
                           'ledger_excerpt_core': quote_core[:400], 'ledger_excerpt_addendum': quote_addendum[:200],
                           'metadata_only': metadata_only},
            'verdict': verdict,
            'verdict_normalized': {'MATCH': 'MATCH', 'PARTIAL': 'PARTIAL', 'MISMATCH': 'FAIL', 'FETCH_FAILED': 'FAIL'}[verdict],
            'reading': reading,
        })

    ledger_sha_after = sha256_file(LEDGER)
    summary = {'checked': len(results), 'MATCH': 0, 'PARTIAL': 0, 'MISMATCH': 0, 'FETCH_FAILED': 0}
    for r in results:
        summary[r['verdict']] = summary.get(r['verdict'], 0) + 1
    hard = [{'citation_id': r['citation_id'], 'verdict': r['verdict'], 'why': r['reading'],
             'class_mapping': r['class_mapping'], 'used_by_theorems': r['used_by_theorems']}
            for r in results if r['verdict'] in ('MISMATCH', 'FETCH_FAILED')]
    classes = sorted({t.strip() for r in results for t in r['class_mapping'].split(';') if t.strip().startswith('AF-')})
    art = {
        'schema_version': '0.1', 'artifact_type': 'l1_spotcheck', 'node_id': 'L1', 'gate': 'G-LIT',
        'task_id': 'astra-life02-l1-spotcheck', 'assignment_event_id': 'astra-life02-l1-spotcheck',
        'review_id': f'l1-spotcheck-049-{datetime.datetime.now().strftime("%Y%m%dT%H%M%S")}',
        'actor': 'worker-049', 'reviewer': 'worker-049', 'created_at': now(), 'check_number': 5,
        'independent_of': [
            'reviews/L1-spotcheck-10.json (flash-10, rows 1-20, earlier ledger sha fe4b48bb)',
            'reviews/L1-spotcheck-11.json (flash-11, rows 21-40, earlier ledger sha fe4b48bb)',
            'artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json (worker-07, rows 41-95 at this sha)',
            'artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json (worker-086, rows 1-40,96,97 at this sha)',
            'in-flight freezes at 00:18 excluded from the sample: worker-006 (SRC-040,047,048,078,082-085), worker-077 (SRC-021,040,042,061)',
        ],
        'independence_note': ('reviewer worker-049 is distinct from flash-10, flash-11, worker-07, worker-086 and from the in-flight '
                              'worker-006/worker-077 freezes; the 12 sampled rows were never re-fetched at ledger sha 315c19145065 by any of them; '
                              'all raw responses were re-fetched from primary APIs, no ledger text was used as evidence.'),
        'supersedes': ('artifacts/worker-049/l1_spotcheck/sample_manifest.json - an orphaned pre-fetch freeze written at 00:15:47 by the killed '
                       'earlier instance of slot 049 (worker-049-20260912T001230-897883); it performed no fetch, wrote no raw body, and is '
                       'superseded by this artifact for slot 049. Its sample overlapped SRC-056 and SRC-091, both re-fetched live here.'),
        'inputs': {'ledger/citation_audit.csv': {'sha256_before_fetch': ledger_sha_before, 'sha256_after_fetch': ledger_sha_after,
                                                 'pinned': PINNED, 'drifted_during_fetch': ledger_sha_before != ledger_sha_after,
                                                 'data_rows': len(rows)}},
        'sampling_rule': freeze['rule'], 'sample_rows': freeze['sample_rows'], 'sample_ids': freeze['sample_ids'],
        'method': {
            'locator_policy': ('arxiv_id -> export.arxiv.org API id_list (abs landing page fallback on rate limit); else doi -> api.crossref.org; '
                               'else INSPIRE/OpenAlex record URL in evidence_url; else evidence_url; ledger exact_locator search queries are not used as evidence'),
            'secondary': 'journal DOI (non-arXiv) cross-checked at api.crossref.org to resolve arXiv-v1 year vs published year',
            'network': 'live re-fetch via urllib, worker-049; raw body written to raw/ and sha256 recorded before parsing; bodies from the earlier pass of this same task are byte-identical cache reuse (flagged per row)',
            'comparison': ('math-aware title token sequence (LaTeX $, ^, _, braces stripped); excerpt prefix stripped and LaTeX stripped; token-multiset coverage of the cited '
                           'excerpt against the fetched abstract plus ordered ratio; year confirmed by primary or journal-DOI secondary; author surnames compared'),
            'verdicts': 'MATCH | PARTIAL (year convention, locator quality, or excerpt not re-checkable) | MISMATCH (=FAIL) | FETCH_FAILED',
            'targeted_search': "SRC-066 only: ledger has no DOI and its venue year is marked 'per secondary citation'; one declared OpenAlex title search resolves year/venue/DOI, recorded as targeted_search evidence and flagged in the reading",
        },
        'class_coverage_from_class_mapping': classes,
        'results': results, 'summary': summary, 'hard_failures': hard,
        'falsifier': ('A re-fetch of any sampled row whose raw body hash differs from the recorded raw_sha256, or whose fetched title/abstract '
                      'contradicts the recorded comparison, or a ledger hash that is not 315c19145065, falsifies this spot check.'),
        'non_claims': ['spot check only; not a gate verdict, not a node status, not a validation_status',
                       'class_mapping is reported as recorded in the ledger; no class-separation verdict is made here',
                       'absence of a mismatch on 12 sampled rows is not evidence that the other 85 rows are correct'],
        'raw_evidence': {'fetch_log': 'artifacts/worker-049/l1_spotcheck/fetch_log.tsv',
                         'raw_dir': 'artifacts/worker-049/l1_spotcheck/raw/',
                         'sample_freeze': 'artifacts/worker-049/l1_spotcheck/sample_freeze.json'},
    }
    out = os.path.join(OUTDIR, 'spotcheck-l1-049.json')
    json.dump(art, open(out, 'w'), indent=1)
    with open(out + '.sha256', 'w') as fh:
        fh.write(sha256_file(out) + '  ' + os.path.basename(out) + '\n')
    print('WROTE', out, sha256_file(out))
    print('SUMMARY', json.dumps(summary))
    print('LEDGER drifted:', ledger_sha_before != ledger_sha_after)
    return 0


if __name__ == '__main__':
    sys.exit(main())
