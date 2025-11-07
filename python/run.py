from lxml import etree
import argparse
from pathlib import Path
import sys

def validate(xml_path: Path, xsd_path: Path) -> bool:
    schema_doc = etree.parse(str(xsd_path))
    schema = etree.XMLSchema(schema_doc)
    doc = etree.parse(str(xml_path))
    is_valid = schema.validate(doc)
    if not is_valid:
        for e in schema.error_log:
            print(f"XSD ERROR: line {e.line}: {e.message}", file=sys.stderr)
    return is_valid

def transform(xml_path: Path, xsl_path: Path, out_path: Path | None) -> str:
    doc = etree.parse(str(xml_path))
    xslt = etree.XSLT(etree.parse(str(xsl_path)))
    result = xslt(doc)
    output_bytes = etree.tostring(result, pretty_print=True, encoding='UTF-8')
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(output_bytes)
    return output_bytes.decode("utf-8", errors="ignore")

def main():
    p = argparse.ArgumentParser(description="Validate XML against XSD and apply XSLT.")
    p.add_argument('--xml', required=True, type=Path, help="Input XML file")
    p.add_argument('--xsd', required=True, type=Path, help="XSD schema file")
    p.add_argument('--validate', action='store_true', help="Validate only")
    p.add_argument('--xsl', type=Path, help="XSLT stylesheet to apply")
    p.add_argument('--out', type=Path, help="Output file path")
    args = p.parse_args()

    ok = validate(args.xml, args.xsd)
    print("VALID" if ok else "INVALID")
    if not ok and args.xsl:
        print("Aborting transform due to invalid XML.", file=sys.stderr)
        sys.exit(1)

    if args.xsl:
        output = transform(args.xml, args.xsl, args.out)
        if not args.out:
            print(output)

if __name__ == '__main__':
    main()
