"""Bounded replay evidence and citation validation. No network or host actions."""
import datetime
import json
import math

def number(value, limit=2**60):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= limit:
        raise ValueError('Invalid measurement')
    return value

def label(value, limit=120):
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError('Invalid label')
    return value

def frames_from(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 2:
        raise ValueError('Select one moment and optionally an earlier baseline')
    result = []
    for raw in value:
        if not isinstance(raw, dict) or raw.get('source') not in ('demo', 'live'):
            raise ValueError('Invalid replay source')
        stamp = label(raw.get('at'), 40)
        date = datetime.datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        if date.tzinfo is None:
            raise ValueError('Replay time needs a timezone')
        services = raw.get('services')
        if not isinstance(services, list) or len(services) > 64:
            raise ValueError('Invalid service sample')
        rows, seen = [], set()
        for s in services:
            if not isinstance(s, dict):
                raise ValueError('Invalid service')
            identity = label(s.get('id'), 80)
            if identity in seen:
                raise ValueError('Duplicate service')
            seen.add(identity)
            rows.append(dict(id=identity, name=label(s.get('name')), cpu=number(s.get('cpu'), 100000), mem=number(s.get('mem'), 100), offline=s.get('offline') is True, unknown=s.get('unknown') is True, state=label(s.get('state', 'unknown'), 30), health=label(s.get('health', 'unknown'), 30)))
        for row in rows:
            if row['unknown']:
                row.update(cpu=None, mem=None)
        hardware = raw.get('hardware')
        clean = None
        if hardware is not None:
            if not isinstance(hardware, dict) or hardware.get('source') != ('simulated' if raw['source'] == 'demo' else 'system'):
                raise ValueError('Hardware source does not match replay')
            memory = hardware.get('memory')
            if memory is not None:
                if not isinstance(memory, dict):
                    raise ValueError('Invalid RAM')
                used, total = number(memory.get('usedBytes')), number(memory.get('totalBytes'))
                if used is not None and total is not None and (total <= 0 or used > total):
                    raise ValueError('Invalid RAM range')
                memory = dict(usedBytes=used, totalBytes=total)
            gpus = hardware.get('gpus', [])
            if not isinstance(gpus, list) or len(gpus) > 16:
                raise ValueError('Invalid GPU sample')
            devices = []
            for g in gpus:
                if not isinstance(g, dict):
                    raise ValueError('Invalid GPU')
                used, total = number(g.get('memoryUsedBytes')), number(g.get('memoryTotalBytes'))
                if used is not None and total is not None and (total <= 0 or used > total):
                    raise ValueError('Invalid VRAM range')
                devices.append(dict(name=label(g.get('name')), utilization=number(g.get('utilization'), 100), memoryUsedBytes=used, memoryTotalBytes=total))
            clean = dict(source=hardware['source'], memory=memory, gpus=devices)
        result.append(dict(at=stamp, source=raw['source'], servicesKnown=raw.get('servicesKnown') is not False, services=rows, hardware=clean))
    if len({r['source'] for r in result}) != 1:
        raise ValueError('Compare moments from the same source')
    if len(result) == 2 and datetime.datetime.fromisoformat(result[0]['at'].replace('Z', '+00:00')) > datetime.datetime.fromisoformat(result[1]['at'].replace('Z', '+00:00')):
        raise ValueError('Baseline must precede the selected moment')
    return result

def evidence_for(frames):
    facts = []
    def add(i, text):
        facts.append(dict(id='E'+str(len(facts)+1), frameIndex=i, at=frames[i]['at'], text=text))
    def fmt(v):
        return 'unavailable' if v is None else str(round(v, 2))
    for i, f in enumerate(frames):
        rows = f['services']
        unknown = sum(s['unknown'] for s in rows)
        offline = sum(s['offline'] and not s['unknown'] for s in rows)
        if not f['servicesKnown']:
            add(i, f['source']+' replay supplied by the browser; service observations unavailable. Counts are unconfirmed.')
        else:
            add(i, f['source']+' replay supplied by the browser; '+str(len(rows))+' services, '+str(offline)+' confirmed offline, '+str(unknown)+' unknown. Running is not proof of application health.')
        h = f['hardware']
        m = h.get('memory') if h else None
        add(i, 'Host RAM bytes used/total: '+(fmt(m['usedBytes'])+'/'+fmt(m['totalBytes']) if m else 'unavailable')+'.')
        if not h or not h['gpus']:
            add(i, 'GPU readings unavailable; no per-service GPU attribution was measured.')
        else:
            for g in h['gpus'][:4]:
                add(i, json.dumps(g['name'])+' GPU '+fmt(g['utilization'])+'%; VRAM bytes '+fmt(g['memoryUsedBytes'])+'/'+fmt(g['memoryTotalBytes'])+'. Whole-device measurements include other host workloads; no per-service attribution.')
        chosen = sorted(rows, key=lambda s: (not (s['unknown'] or s['offline']), -(s['cpu'] or 0)))[:6]
        for s in chosen:
            add(i, json.dumps(s['name'])+': CPU '+fmt(s['cpu'])+'%; container RAM '+fmt(s['mem'])+'%; state '+('unknown' if s['unknown'] else 'offline' if s['offline'] else s['state'])+'; health '+s['health']+'.')
    if len(frames) == 2:
        before, after = frames
        def delta(a, b):
            if a is None or b is None:
                return 'unavailable'
            change = b-a
            return ('+' if change >= 0 else '')+str(round(change, 2))
        old_h, new_h = before['hardware'], after['hardware']
        old_m = old_h.get('memory') if old_h else None
        new_m = new_h.get('memory') if new_h else None
        if old_m and new_m:
            add(1, 'COMPUTED CHANGE: host RAM used bytes '+delta(old_m['usedBytes'], new_m['usedBytes'])+'. This is host RAM, distinct from all container RAM percentages.')
        if old_h and new_h:
            for a, b in list(zip(old_h['gpus'], new_h['gpus']))[:4]:
                if a['name'] == b['name']:
                    add(1, 'COMPUTED CHANGE: '+json.dumps(b['name'])+' GPU utilization '+delta(a['utilization'], b['utilization'])+' percentage points; VRAM used bytes '+delta(a['memoryUsedBytes'], b['memoryUsedBytes'])+'. Device-wide; cause and service attribution are not established.')
        old_rows = {s['id']:s for s in before['services']}
        pairs = [(old_rows[s['id']],s) for s in after['services'] if s['id'] in old_rows]
        pairs.sort(key=lambda pair: (pair[0]['offline'] == pair[1]['offline'], -abs((pair[1]['cpu'] or 0)-(pair[0]['cpu'] or 0)), pair[1]['id']))
        for a, b in pairs[:6]:
            state_a = 'unknown' if a['unknown'] else 'offline' if a['offline'] else a['state']
            state_b = 'unknown' if b['unknown'] else 'offline' if b['offline'] else b['state']
            add(1, 'COMPUTED CHANGE: '+json.dumps(b['name'])+' CPU '+delta(a['cpu'], b['cpu'])+' percentage points; container RAM '+delta(a['mem'], b['mem'])+' percentage points; state '+state_a+' -> '+state_b+'. A +0 change means unchanged, not increased.')
    return facts

def validated_analysis(text, facts):
    raw = text.strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    data = json.loads(raw)
    known = {f['id'] for f in facts}
    def row(value):
        if not isinstance(value, dict):
            raise ValueError('Unstructured analysis')
        text = label(value.get('text'), 1200)
        ids = value.get('evidenceIds')
        if not text or not isinstance(ids, list) or not 1 <= len(ids) <= 12 or any(not isinstance(x, str) or x not in known for x in ids):
            raise ValueError('Analysis cites unknown evidence')
        return dict(text=text, evidenceIds=list(dict.fromkeys(ids)))
    if not isinstance(data, dict) or not isinstance(data.get('observations'), list) or not 1 <= len(data['observations']) <= 6 or not isinstance(data.get('nextChecks'), list) or not 1 <= len(data['nextChecks']) <= 4:
        raise ValueError('Invalid analysis structure')
    return dict(summary=row(data.get('summary')), observations=[row(x) for x in data['observations']], nextChecks=[row(x) for x in data['nextChecks']])
