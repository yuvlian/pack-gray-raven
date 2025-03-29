import re
from typing import List

# this code is ass lmao

CLASS_NAME_RE = re.compile(r'\b(?:class|struct)\s+(\w+)\s*// TypeDefIndex:')
FIELD_RE = re.compile(r'^\s*(?:public|private|protected)?\s*([\w<>\[\],\s]+)\s+(\w+);\s*// 0x')

TYPE_MAP = {
    "Dictionary": "Dict",
    "DateTime": "datetime",
    "HashSet": "Set",
    "dynamic": "Any",
    "decimal": "float",
    "double": "float",
    "float": "float",
    "object": "dict",
    "string": "str",
    "char": "str",
    "sbyte": "int",
    "short": "int",
    "ushort": "int",
    "uint": "int",
    "ulong": "int",
    "long": "int",
    "byte": "int",
    "int": "int",
    "bool": "bool",
    "List": "List"
}


def parse_generic(type_str: str) -> str:
    stack: List[str] = []

    for char in type_str:
        if char == "<":
            stack.append("[")
        elif char == ">":
            stack.append("]")
        else:
            stack.append(char)
    
    r = "".join(stack)
    
    for csharp, py in TYPE_MAP.items():
        r = r.replace(csharp, py)
    
    return r


def csharp_type_to_python(csharp_type: str) -> str:
    csharp_type = csharp_type.strip()
    is_optional = csharp_type.endswith("?")

    if is_optional:
        csharp_type = csharp_type[:-1]

    if csharp_type.endswith("[]"):
        t = csharp_type[:-2]
        if t == "byte":
            return f"Optional[bytes]" if is_optional else "bytes"
        else:
            return f"Optional[List[{t}]]" if is_optional else f"List[{t}]"

    mapped_type = parse_generic(csharp_type)

    return f"Optional[{mapped_type}]" if is_optional else mapped_type


def parse_msgpack_dump(dump_cs: str, output_file: str) -> None:
    parsed = [
        "from pydantic import BaseModel\n" +
        "from typing import Any, Dict, List, Optional, Set\n" +
        "from datetime import datetime"
    ]

    in_msgpack, in_fields = False, False
    
    with open(dump_cs, 'r', encoding='utf-8') as file:
        for i, line in enumerate(file):
            line = line.strip()

            if len(line) <= 0:
                pass

            match line:
                case l if "[MessagePack" in l and not in_msgpack:
                    in_msgpack = True

                case l if "[MessagePack" in l and in_msgpack:
                    p_len = len(parsed)
                    if p_len > 0:
                        n = min(i - 1, p_len - 1)
                        if n >= 0 and "class" in parsed[n]:
                            parsed.append("    pass")

                case l if ("class" in l or "struct" in l) and in_msgpack:
                    if m := CLASS_NAME_RE.search(l):
                        parsed.append(f"\nclass {m.group(1)}(BaseModel):")

                case l if "// Fields" in l and in_msgpack and not in_fields:
                    in_fields = True

                case l if "; // 0x" in l and in_msgpack and in_fields:
                    if m := FIELD_RE.search(l):
                        field_type, field_name = m.groups()
                        p_type = csharp_type_to_python(field_type)
                        parsed.append(f"    {field_name}: {p_type}")

                case l if ("// Methods" in l or ".ctor()" in l) and in_msgpack and in_fields:
                    in_msgpack = False
                    in_fields = False

                case _:
                    pass
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write('\n'.join(parsed))
    
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    parse_msgpack_dump("dump.cs", "output.py")
