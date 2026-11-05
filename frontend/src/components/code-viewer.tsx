"use client";

import { useEffect, useMemo, useRef } from "react";
import { cn } from "./ui";

const COBOL_KW = new Set(
  (
    "ACCEPT ADD ALSO AND ANY BY CALL COMPUTE CONTINUE COPY DISPLAY DIVIDE DIVISION ELSE END-ADD END-CALL END-COMPUTE END-EVALUATE END-IF END-PERFORM END-STRING " +
    "EVALUATE EXIT FROM GIVING GO GOBACK IF INITIALIZE INTO MOVE MULTIPLY NOT OCCURS OF OR OTHER PERFORM PIC PICTURE PROCEDURE PROGRAM-ID REDEFINES ROUNDED " +
    "SECTION SET SIZE ERROR STOP RUN STRING SUBTRACT THRU THROUGH TIMES TO TRUE FALSE UNTIL USING VALUE VALUES VARYING WHEN WORKING-STORAGE LINKAGE FILE " +
    "IDENTIFICATION ENVIRONMENT DATA CONFIGURATION INPUT-OUTPUT FILE-CONTROL SELECT ASSIGN FD COMP COMP-3 COMP-5 BINARY PACKED-DECIMAL DELIMITED SPACES SPACE " +
    "ZERO ZEROS ZEROES INSPECT OPEN CLOSE READ WRITE REWRITE TALLYING FOR ALL NUMERIC SIGN LEADING TRAILING SEPARATE IS EQUAL GREATER LESS THAN WITH POINTER " +
    "END PROGRAM AUTHOR DATE-WRITTEN REMARKS OBJECT-COMPUTER SOURCE-COMPUTER ON EXTEND OUTPUT INPUT I-O ORGANIZATION LINE SEQUENTIAL STATUS FILLER INDEXED " +
    "FUNCTION RETURNING REFERENCE CONTENT AT"
  ).split(" "),
);

const PY_KW = new Set(
  "False None True and as assert break class continue def del elif else except finally for from if import in is lambda not or pass raise return try while with yield self".split(" "),
);

function esc(s: string) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function highlightCobol(line: string, fixed: boolean): string {
  let prefix = "";
  let body = line;
  if (fixed && line.length >= 7) {
    prefix = `<span class="tok-seq">${esc(line.slice(0, 6))}</span>`;
    const ind = line[6];
    if (ind === "*" || ind === "/") return prefix + `<span class="tok-com">${esc(line.slice(6))}</span>`;
    prefix += esc(ind);
    body = line.slice(7);
  }
  const ci = body.indexOf("*>");
  let comment = "";
  if (ci >= 0 && (body.slice(0, ci).split('"').length - 1) % 2 === 0) {
    comment = `<span class="tok-com">${esc(body.slice(ci))}</span>`;
    body = body.slice(0, ci);
  }
  const out = body.replace(/("[^"]*"?|'[^']*'?)|(\b\d+(?:\.\d+)?\b)|([A-Za-z][A-Za-z0-9-]*)|([^"'A-Za-z0-9]+)/g, (m, str, num, word, other) => {
    if (str) return `<span class="tok-str">${esc(str)}</span>`;
    if (num) return `<span class="tok-num">${esc(num)}</span>`;
    if (word) return COBOL_KW.has(word.toUpperCase()) ? `<span class="tok-kw">${esc(word)}</span>` : esc(word);
    return esc(other ?? m);
  });
  return prefix + out + comment;
}

function highlightPython(line: string): string {
  const hash = line.search(/#(?=(?:[^'"]|'[^']*'|"[^"]*")*$)/);
  let comment = "";
  let body = line;
  if (hash >= 0) {
    comment = `<span class="tok-com">${esc(line.slice(hash))}</span>`;
    body = line.slice(0, hash);
  }
  const out = body.replace(/("""|'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)(\s*\()?|([^"'A-Za-z0-9_]+)/g, (m, str, num, word, paren, other) => {
    if (str) return `<span class="tok-str">${esc(str)}</span>`;
    if (num) return `<span class="tok-num">${esc(num)}</span>`;
    if (word) {
      if (PY_KW.has(word)) return `<span class="tok-kw">${esc(word)}</span>${paren ? esc(paren) : ""}`;
      if (paren) return `<span class="tok-fn">${esc(word)}</span>${esc(paren)}`;
      return esc(word);
    }
    return esc(other ?? m);
  });
  return out + comment;
}

export interface CodeViewerProps {
  text: string;
  language: "cobol" | "python" | "text" | "json";
  highlight?: [number, number] | null;
  marks?: Set<number>;
  onLineClick?: (line: number) => void;
  className?: string;
  maxHeight?: string;
  fixedFormat?: boolean;
  scrollKey?: string;
  startLine?: number;
}

export function CodeViewer({ text, language, highlight, marks, onLineClick, className, maxHeight = "70vh", fixedFormat = true, scrollKey, startLine = 1 }: CodeViewerProps) {
  const lines = useMemo(() => text.replace(/\n$/, "").split("\n"), [text]);
  const html = useMemo(
    () => lines.map((l) => (language === "cobol" ? highlightCobol(l, fixedFormat) : language === "python" ? highlightPython(l) : esc(l))),
    [lines, language, fixedFormat],
  );
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!highlight || !box.current) return;
    const el = box.current.querySelector<HTMLElement>(`[data-line="${highlight[0]}"]`);
    if (el) box.current.scrollTo({ top: Math.max(0, el.offsetTop - 80), behavior: "smooth" });
  }, [highlight, scrollKey]);
  const gutter = String(lines.length + startLine).length;
  return (
    <div ref={box} className={cn("relative overflow-auto rounded-lg border border-ink-600 bg-ink-950 font-mono text-[12.5px] leading-[1.6]", className)} style={{ maxHeight }}>
      <table className="w-full border-collapse">
        <tbody>
          {html.map((h, i) => {
            const n = i + startLine;
            const hl = !!highlight && n >= highlight[0] && n <= highlight[1];
            const marked = marks?.has(n);
            return (
              <tr key={n} data-line={n} data-hl={hl} className={cn("code-line", onLineClick && "cursor-pointer hover:bg-ink-800/70")} onClick={() => onLineClick?.(n)}>
                <td className={cn("sticky left-0 select-none border-r border-ink-700 bg-ink-950 pr-3 pl-3 text-right align-top text-fog-500", marked && "text-phoenix-400")} style={{ width: `${gutter + 3}ch` }}>
                  {marked ? "●" : ""}
                  {n}
                </td>
                <td className="whitespace-pre pr-6 pl-4 text-fog-100" dangerouslySetInnerHTML={{ __html: h || " " }} />
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
