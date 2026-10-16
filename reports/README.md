# Reports

| Round | Topic | Deadline | Status | Report |
|---|---|---|---|---|
| 1 | Strategic asset allocation | TBD | Done | [round-1/round-1-saa.pdf](round-1/round-1-saa.pdf) |
| 2 | Equity | TBD | Not started | — |
| 3 | Quant & macro | TBD | Not started | — |

## Next report
1. Copy `template/report-template.html` to `round-N/round-N-<topic>.html`; put its figures in the same folder.
2. Replace every `[placeholder]` (including `Round [N]` in the `@page` rules) and add one chapter section per part.
3. Print from that folder:
   `chrome --headless --no-pdf-header-footer --print-to-pdf=round-N-<topic>.pdf round-N-<topic>.html`
4. Fill in the row above and link the PDF in the site footer ("Letters") in `index.html`.

`round-1/round-1-saa.html` is a complete example.
