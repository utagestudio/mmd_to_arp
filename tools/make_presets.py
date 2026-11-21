"""Write the Quick Rig preset files defined in mmd_to_arp/mapping.py.

Usage: python tools/make_presets.py [output_dir]   (default: presets)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mmd_to_arp'))
import mapping  # noqa: E402


def write_preset(path, preset):
    # Quick Rig reads only the first line, with open() in the OS default encoding
    # (cp932 / cp1252 on Windows), then ast.literal_eval. Write pure ASCII with
    # \uXXXX escapes so Japanese bone names survive on every OS.
    text = repr(preset).encode('ascii', 'backslashreplace').decode('ascii')
    with open(path, 'w', encoding='ascii', newline='\n') as f:
        f.write(text + '\n')


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'presets'
    os.makedirs(out, exist_ok=True)
    for name in mapping.preset_names():
        write_preset(os.path.join(out, name + '.py'), mapping.get_preset(name))
        print('wrote', name + '.py')


if __name__ == '__main__':
    main()
