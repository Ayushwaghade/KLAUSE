import os, json

groups = {
    'app_tools.py': 'window', 'automation_tools.py': 'automation', 'browser_tools.py': 'browser',
    'clipboard_tools.py': 'filesystem', 'filesystem_tools.py': 'filesystem', 'git_tools.py': 'terminal',
    'kb_tools.py': 'memory', 'memory_tools.py': 'memory', 'obsidian_tools.py': 'memory',
    'project_tools.py': 'core', 'rules_tools.py': 'core', 'session_tools.py': 'core',
    'skill_repo_tools.py': 'automation', 'system_tools.py': 'core', 'terminal_tools.py': 'terminal',
    'vision_tools.py': 'vision', 'vscode_tools.py': 'terminal', 'window_tools.py': 'window'
}
base_dir = r'e:\KLAUSE\app\tools'
out = []
for f, g in groups.items():
    p = os.path.join(base_dir, f)
    with open(p, 'r') as file: lines = file.readlines()
    chunks = []
    for i, line in enumerate(lines):
        if line.strip().startswith('name='):
            start = i
            while start >= 0 and not lines[start].startswith('@tool'):
                start -= 1
            if start >= 0:
                target = ''.join(lines[start:i+1])
                replacement = target + f'    group=\"{g}\",\n'
                chunks.append({
                    'AllowMultiple': False,
                    'StartLine': start+1,
                    'EndLine': i+1,
                    'TargetContent': target,
                    'ReplacementContent': replacement
                })
    if chunks:
        out.append({'TargetFile': p, 'Instruction': 'Add group to tools', 'Description': 'Add group parameter', 'ReplacementChunks': chunks, 'toolSummary': f'Edit {f}', 'toolAction': f'Editing {f}'})

with open('calls.json', 'w') as out_f:
    json.dump(out, out_f, indent=2)
