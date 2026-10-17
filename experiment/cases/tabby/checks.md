# Tabby: the checks

Fixed before any trial. `score.py` runs them against the merged app; the reference build
in `reference/` passes all 9; the empty starter passes only C3, since an unbuilt app also
answers 404. The order used throughout is `coffee:3.50:2 bagel:4.25:1`.

| Id | Event | Check | Expected |
| --- | --- | --- | --- |
| C1 | plain build | `bill <order> --tip 18` | `subtotal: 11.25`, `tip: 2.03` |
| C2 | plain build | `show <id>` | the same bill, `subtotal: 11.25`, `tip: 2.03` |
| C3 | plain build | `show 999`, `GET /bills/999` | one `error:` line, exit status 1; the API answers 404 |
| C4 | plain build | `GET /bills/<id>` | JSON numbers `id`, `subtotal`, `tip`, `total` |
| C5 | plan change | `bill <order> --tip 18` | `service: 0.56`, right after `subtotal:` |
| C6 | plan change | `bill <order> --tip 18` | `total: 13.84` |
| C7 | two developers disagree | `bill <order>` (no `--tip`) | `tip: 2.25`, `total: 14.06` (the lead's 20%) |
| C8 | two developers disagree | `POST /bills` without `tip_percent` | `tip` 2.25 |
| C9 | a note against the plan | `split <id> --people 3` | `per_person: 4.62` (rounded up) |

## The events

- **Plan change** (phase 2): a 5% service charge and a new `service` field, which both
  parts must build.
- **Two developers disagree** (phase 2): the API's developer wants an 18% default tip,
  the command line's developer wants it to send 15%. The plan doesn't say. The lead's
  sheet says 20%, so C7 and C8 only pass if the question reaches the lead.
- **A note against the plan** (phase 1): the API's developer asks for the split rounded
  half up; R-2 says rounded up.
