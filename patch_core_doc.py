import re, sys

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    content = f.read()

# Extrait le bloc <configObject name="identify">...</configObject>
m = re.search(r'\s*<configObject name="identify".*?</configObject>', content, re.DOTALL)
if not m:
    print("Bloc 'identify' introuvable — peut-être déjà patché ou absent.")
    sys.exit(1)

identify_block = m.group(0)
content_without = content[:m.start()] + content[m.end():]

# Insère ce bloc juste avant la fermeture de configInfo name="res_pjsip"
pattern = r'(<configInfo name="res_pjsip".*?)(</configInfo>)'
def insert(match):
    return match.group(1) + identify_block + "\n" + match.group(2)

new_content, n = re.subn(pattern, insert, content_without, count=1, flags=re.DOTALL)
if n == 0:
    print("Bloc configInfo name='res_pjsip' introuvable.")
    sys.exit(1)

# Validation XML
import xml.dom.minidom as minidom
minidom.parseString(new_content)

out_path = path.replace(".xml", ".patched.xml")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(new_content)
print(f"OK — fichier validé et écrit dans {out_path}")
