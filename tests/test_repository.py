import importlib.util
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]


def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


class RepositoryTests(unittest.TestCase):
    def test_default_oci_isolation(self):
        m=module('prepare','prepare-runc.py')
        cfg=m.specification(Path('/runtime'),Path('/state'),Path('/work'))
        self.assertEqual(cfg['process']['user']['uid'],1000)
        self.assertTrue(cfg['process']['noNewPrivileges'])
        self.assertTrue(cfg['root']['readonly'])
        self.assertTrue(all(not v for v in cfg['process']['capabilities'].values()))
        self.assertEqual(cfg['linux']['seccomp']['defaultAction'],'SCMP_ACT_ERRNO')
        self.assertEqual(cfg['linux']['resources']['memory']['limit'],192*1024*1024)
        self.assertEqual(cfg['process']['user']['additionalGids'],[])
        self.assertEqual(m.specification(Path('/r'),Path('/s'),Path('/w'),inet=True)['process']['user']['additionalGids'],[3003])
        self.assertNotIn('/var/run/docker.sock',json.dumps(cfg))
        self.assertNotIn('network',[n['type'] for n in cfg['linux']['namespaces']])  # documented host network

    def test_independent_locked_tracks(self):
        for flavor in ('standard','minimal'):
            root=ROOT/'tracks'/flavor
            inputs=json.loads((root/'inputs.json').read_text())
            package=json.loads((root/'package.json').read_text())
            lock=json.loads((root/'package-lock.json').read_text())
            self.assertEqual(package['dependencies']['@earendil-works/pi-coding-agent'],inputs['pi'])
            self.assertEqual(lock['packages']['']['dependencies'],package['dependencies'])
            self.assertRegex(inputs['alpine'],r'@sha256:[a-f0-9]{64}$')
            self.assertTrue(all('=' in item for item in inputs['packages']))
        guard=json.loads((ROOT/'tracks/minimal/patch-inputs.json').read_text())
        self.assertEqual(len(guard['source_files']),9)
        self.assertEqual(guard['pi'],json.loads((ROOT/'tracks/minimal/inputs.json').read_text())['pi'])

    def test_no_private_publication_inputs(self):
        tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
        bad=[r'-----BEGIN (?:OPENSSH|RSA|EC|PRIVATE) PRIVATE KEY-----',r'(?i)gh[pousr]_[A-Za-z0-9]{25,}',r'192\.168\.\d+\.\d+',r'/Users/[^/]+/\.openclaw/',r'(?i)sk-(?:proj-)?[A-Za-z0-9_-]{30,}']
        # Scan distributable source, not this file's detection expressions.
        for name in tracked:
            if not name or name==str(Path(__file__).relative_to(ROOT)):
                continue
            self.assertNotRegex(name,r'(^|/)(private|state|sessions|node_modules)/')
            self.assertNotIn(Path(name).name,['auth.json','models.json','agent-private.json','id_ed25519'])
            data=(ROOT/name).read_text()
            for pattern in bad:self.assertNotRegex(data,pattern,name)

    def test_apk_source_inventory_parser(self):
        m=module('sources','sources.py')
        records=list(m.apk_records('P:example\nV:1.0-r0\no:source\nL:MIT\nc:'+'a'*40+'\nA:armv7\n\nF:usr\n'))
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['origin'],'source')


if __name__=='__main__':unittest.main()
