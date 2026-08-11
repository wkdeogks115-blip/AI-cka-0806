from __future__ import annotations
import argparse, json
from pathlib import Path
from preview_engine import build_preview

def main():
    ap=argparse.ArgumentParser(description="Factory B standalone preview — UX rehearsal only")
    ap.add_argument("request", help="JSON request file")
    ap.add_argument("--output", help="optional JSON output file")
    args=ap.parse_args()
    req=json.loads(Path(args.request).read_text(encoding="utf-8"))
    out=build_preview(req)
    text=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
    print(text,end="")
    if args.output:
        Path(args.output).write_text(text,encoding="utf-8")
if __name__=="__main__":
    main()
