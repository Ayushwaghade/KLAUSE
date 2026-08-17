import os
import re

groups = {
    'app_tools.py': 'window',
    'automation_tools.py': 'automation',
    'browser_tools.py': 'browser',
    'clipboard_tools.py': 'filesystem',
    'filesystem_tools.py': 'filesystem',
    'git_tools.py': 'terminal',
    'kb_tools.py': 'memory',
    'memory_tools.py': 'memory',
    'obsidian_tools.py': 'memory',
    'project_tools.py': 'core',
    'rules_tools.py': 'core',
    'session_tools.py': 'core',
    'skill_repo_tools.py': 'automation',
    'system_tools.py': 'core',
    'terminal_tools.py': 'terminal',
    'vision_tools.py': 'vision',
    'vscode_tools.py': 'terminal',
    'window_tools.py': 'window'
}

base_dir = r'e:\KLAUSE\app\tools'

for filename, group in groups.items():
    filepath = os.path.join(base_dir, filename)
    if not os.path.exists(filepath):
        print(f"Skipping {filename} - not found")
        continue
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    def repl(m):
        return m.group(1) + f'\n    group="{group}",'
        
    new_content = re.sub(r'(name\s*=\s*[\'"][^\'"]+[\'"]\s*,)', repl, content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
print('Updates completed successfully.')
