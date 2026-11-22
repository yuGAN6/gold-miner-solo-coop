"""Build a local two-player edition of all four single-player SWFs."""
import copy
import json
import pathlib
import re
import struct
import subprocess
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = ROOT / 'mod-work'
JAVA = next((ROOT / 'mod-tools/vendor/java').rglob('java.exe'))
FFDEC = ROOT / 'mod-tools/vendor/ffdec/ffdec.jar'


def ffdec(*args):
    result = subprocess.run([str(JAVA), '-Djava.awt.headless=true', '-jar', str(FFDEC), *map(str, args)],
                            cwd=ROOT, capture_output=True, encoding='utf8', errors='replace')
    with (WORK / 'build.log').open('a', encoding='utf8') as f:
        f.write(result.stdout + result.stderr)
    if result.returncode or re.search(r'(?m)^(?:FAIL|Error:|SEVERE:)', result.stdout + result.stderr):
        raise RuntimeError((result.stdout + result.stderr)[-5000:])


def prepare_edits():
    source = WORK / 'rf-scripts/scripts'
    dest = WORK / 'coop-edits/scripts'
    changed = []
    for p in source.rglob('*.as'):
        s = p.read_text(encoding='utf8')
        new = s
        if 'this.hitTest("_root.T" + x + ".ob.box")' in s:
            # gotoAndStop(2) removes the object. The explicit frame guard also
            # prevents a second claw claiming it in the same render tick.
            new = new.replace('and _parent.busy == 0)',
                              'and _parent.busy == 0 and eval("_root.T" + x)._currentframe == 1)')
        if 'if(eval("/:busy") == 1)' in s:
            new = new.replace('if(eval("/:busy") == 1)',
                              'if(eval("/:busy") == 1 or _root.bsy2 == 1)')
        if new != s:
            out = dest / p.relative_to(source)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(new, encoding='utf8')
            changed.append(str(p.relative_to(source)))
    print('Compiled collision/timer fixes:', len(changed), flush=True)


RENAMES = {'miner': 'mate2', 'bonus': 'prize', 'C': 'P', '/:busy': '/:bsy2',
           '_root.miner': '_root.mate2', '_root.bonus': '_root.prize', '_root.C': '_root.P'}


def patch_actions(hexdata):
    """Only change equal-length AVM1 strings, preserving all branch offsets."""
    data = bytearray.fromhex(hexdata)
    pos = 0
    while pos < len(data):
        op = data[pos]
        pos += 1
        if op < 128:
            continue
        size = struct.unpack_from('<H', data, pos)[0]
        pos += 2
        end = pos + size
        strings = []
        if op == 0x88:  # ConstantPool
            count = struct.unpack_from('<H', data, pos)[0]
            p = pos + 2
            for _ in range(count):
                q = data.index(0, p)
                strings.append((p, q))
                p = q + 1
        elif op == 0x96:  # Push
            p = pos
            while p < end:
                kind = data[p]
                p += 1
                if kind == 0:
                    q = data.index(0, p)
                    strings.append((p, q))
                    p = q + 1
                else:
                    p += {1: 4, 2: 0, 3: 0, 4: 1, 5: 1, 6: 8, 7: 4, 8: 1, 9: 2}[kind]
        elif op in (0x9b, 0x8e, 0x94, 0x8f):
            raise ValueError('Unexpected nested AVM1 block in cloned symbol')
        for a, b in strings:
            value = data[a:b].decode('utf8')
            replacement = RENAMES.get(value, value).encode('utf8')
            assert len(replacement) == b - a
            data[a:b] = replacement
        pos = end
    return data.hex()


def clone_players(xml_in, xml_out):
    tree = ET.parse(xml_in)
    tags = tree.getroot().find('tags')
    originals = list(tags)
    symbols = {int(x.get('spriteId') or x.get('buttonId')): x for x in tags
               if x.get('type') in ('DefineSpriteTag', 'DefineButton2Tag')}
    roots = {int(x.get('characterId')) for x in tags
             if x.get('type') == 'PlaceObject2Tag' and x.get('name') in ('C', 'miner', 'bonus')}
    todo = list(roots)
    seen = set()
    while todo:
        i = todo.pop()
        if i in seen or i not in symbols:
            continue
        seen.add(i)
        todo.extend(int(x.get('characterId')) for x in symbols[i].iter() if x.get('characterId'))
    mapping = {old: 2000 + n for n, old in enumerate(sorted(seen))}
    # Insert a clone immediately after its original definition, so all display
    # dependencies remain defined before any instance is placed.
    clones = {}
    for old in sorted(seen):
        node = copy.deepcopy(symbols[old])
        id_key = 'spriteId' if node.get('type') == 'DefineSpriteTag' else 'buttonId'
        node.set(id_key, str(mapping[old]))
        for x in node.iter():
            if x.get('characterId') and int(x.get('characterId')) in mapping:
                x.set('characterId', str(mapping[int(x.get('characterId'))]))
            if x.get('actionBytes'):
                x.set('actionBytes', patch_actions(x.get('actionBytes')))
            if x.get('type') == 'BUTTONCONDACTION':
                key = int(x.get('condKeyPress', '0'))
                if key:
                    x.set('condKeyPress', str({1: 97, 2: 100, 14: 119, 15: 115}[key]))
        clones[id(symbols[old])] = node

    tags.clear()
    active = {}
    placements = 0
    for node in originals:
        tagtype = node.get('type')
        depth = node.get('depth')
        actor = None
        if tagtype == 'PlaceObject2Tag':
            if node.get('placeFlagHasCharacter') == 'true':
                if node.get('name') in ('C', 'miner', 'bonus'):
                    active[depth] = node.get('name')
                elif depth in active:
                    raise ValueError('Actor depth replaced without removal')
            actor = active.get(depth)
        elif tagtype == 'RemoveObject2Tag':
            actor = active.pop(depth, None)
        twin = None
        if actor:
            twin = copy.deepcopy(node)
            twin.set('depth', str(int(depth) + 1000))
            if tagtype == 'PlaceObject2Tag':
                if twin.get('characterId'):
                    twin.set('characterId', str(mapping[int(twin.get('characterId'))]))
                if twin.get('name'):
                    twin.set('name', RENAMES[actor])
                matrix = node.find('matrix')
                if matrix is not None:
                    x = int(matrix.get('translateX'))
                    matrix.set('translateX', str(x - 1700))
                    twin.find('matrix').set('translateX', str(x + 1700))
                    # Let FFDec recompute the binary MATRIX bit widths.
                placements += 1
        tags.append(node)
        if id(node) in clones:
            tags.append(clones[id(node)])
        if twin is not None:
            tags.append(twin)
    tree.write(xml_out, encoding='utf8', xml_declaration=True)
    return {'clonedSymbols': len(seen), 'actorPlacements': placements, 'mapping': mapping}


def main():
    prepare_edits()
    report = {}
    for variant in ('', 'l10n-cjk', 'l10n-latin', 'l10n-pad'):
        name = variant or 'base'
        original = WORK / 'swf' / variant / 'rf.swf'
        fixed = WORK / (name + '-fixed.swf')
        xml = WORK / (name + '-fixed.xml')
        coopxml = WORK / (name + '-coop.xml')
        out = WORK / 'coop-swf' / variant / 'rf.swf'
        out.parent.mkdir(parents=True, exist_ok=True)
        ffdec('-importScript', original, fixed, WORK / 'coop-edits')
        ffdec('-swf2xml', fixed, xml)
        report[name] = clone_players(xml, coopxml)
        ffdec('-xml2swf', coopxml, out)
        print(name, 'built:', out.stat().st_size, 'bytes', flush=True)
    (WORK / 'build-report.json').write_text(json.dumps(report, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
