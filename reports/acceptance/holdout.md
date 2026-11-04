# Acceptance test 1: held-out texts, 1570-1589

71 texts held out of the index (3,034,851 words of English, regularised spelling, foreign and defective tokens removed); watch list off.

Word statuses are what `desk check` reports by default; the last column is the opt-in phrase heuristic (`--phrases`), measured on the same texts.

| checked against | FLAG /1000 | BORDERLINE /1000 | NOTE /1000 | UNVERIFIED /1000 | phrase flags /1000 (opt-in) |
|---|---:|---:|---:|---:|---:|
| 1589 | 1.065 | 0.551 | 2.673 | 1.268 | 0.337 |
| each text's own year | 1.36 | 1.046 | 3.13 | 1.268 | 0.742 |

Of the FLAGs against 1589, 2056 of 3232 (0.677 per 1,000 words) are capitalised words - mostly names of people and places printed in no other text before 1604; lower-case FLAGs run at 0.388 per 1,000 words.

Most frequent FLAGs (against 1589):

- `theodidactus` ×245 — in A05738 (1581); index's earliest firm date 1620 (A01004); exact
- `abdelmelec` ×60 — in A09826 (1587); index's earliest firm date 1639 (A17474); exact
- `sarcaparillia` ×47 — in A07612 (1580); index's earliest firm date 1616 (A17230); exact
- `heskins'` ×40 — in A68078 (1579); index's earliest firm date 1612 (B12340); exact
- `amusus` ×38 — in A05738 (1581); index's earliest firm date 1666 (A50777); exact
- `nicotiane` ×16 — in A07612 (1580); index's earliest firm date 1615 (A09144); exact
- `reformators` ×15 — in A01304 (1571); index's earliest firm date 1616 (A01958); exact
- `escuerçonera` ×14 — in A07612 (1580); index's earliest firm date 1616 (A17230); spelling variant 'escuerconera'
- `napoly` ×14 — in A09826 (1587); index's earliest firm date 1650 (A77030); exact
- `sveveland` ×14 — in A18640 (1586); index's earliest firm date 1656 (A34262); exact
- `celebin` ×10 — in A09826 (1587); index's earliest firm date 1612 (A01095); exact
- `giafer` ×10 — in A09826 (1587); index's earliest firm date 1612 (A01095); exact
- `wakesses` ×10 — in A13086 (1583); index's earliest firm date 1681 (A44326); exact
- `guaiacan` ×9 — in A07612 (1580); index's earliest firm date 1605 (A20901); exact
- `jusuf` ×9 — in A09826 (1587); index's earliest firm date 1612 (A01095); exact
- `penna` ×8 — in A07612 (1580); index's earliest firm date 1606 (A00909); exact
- `flissing` ×7 — in A09826 (1587); index's earliest firm date 1609 (A68345); exact
- `suriasaro` ×7 — in A09826 (1587); index's earliest firm date 1612 (A01095); exact
- `impliments` ×7 — in A73575 (1589); index's earliest firm date 1641 (A34722); exact
- `windage` ×7 — in A73575 (1589); index's earliest firm date 1649 (A45253); exact
- `estotilande` ×6 — in A02494 (1582); index's earliest firm date 1662 (A37110); exact
- `clario` ×6 — in A09826 (1587); index's earliest firm date 1621 (A12317); exact
- `rotchell` ×6 — in A18737 (1579); index's earliest firm date 1605 (A72050); exact
- `marsden` ×6 — in A21831 (1586); index's earliest firm date 1608 (A15506); exact
- `erasso` ×5 — in A00939 (1580); index's earliest firm date 1612 (A07363); exact

Opt-in phrase-heuristic flags (against the book year) - ordinary later collocations, which is why the heuristic is off by default:

`another edition` ×10, `and cyrill` ×6, `from sinning against` ×5, `pieces of cannon` ×5, `worldly sanctuary` ×4, `work of reconciliation` ×4, `both the guilt` ×3, `of good unto` ×3, `that this means` ×3, `thy lasting` ×3, `a civil use` ×3, `ans in the` ×3, `breaches of this` ×3, `bring forth sin` ×3, `t jer` ×3, `dissenting brethren` ×3, `the dissenting brethren` ×3, `saving repentance` ×3, `puffs up` ×3, `cyrill and` ×3, `young timothy` ×3, `lieutenant colonel to` ×3, `will not beleeue` ×3, `labour to approve` ×2, `are either inward` ×2, `bad children` ×2, `because men kept` ×2, `his heart smote` ×2, `our several places` ×2, `powerful means` ×2

Most frequent UNVERIFIED (not in the index at all):

`nigreponto` ×15, `oluzali` ×14, `despetado` ×13, `roorie` ×13, `dks` ×11, `cefalenia` ×10, `caulleth` ×9, `ruibarbe` ×8, `longsufferinge` ×7, `carapery` ×7, `caphards'` ×7, `zipphora` ×7, `cisill` ×7, `molande` ×6, `sarcaparilla` ×6, `malipetro` ×6, `ailg` ×6, `bactrianians` ×6, `barkage` ×6, `tyncturs` ×5, `arzill` ×5, `gugny` ×5, `thenemy` ×5, `glauburge` ×5, `lakaell` ×5, `wilfforde` ×5, `truncatly` ×5, `militineus` ×4, `siluatico` ×4, `abdelmus` ×4, `couwenstein` ×4, `galleaze` ×4, `alonco` ×4, `pinsnets` ×4, `dbsequys` ×4, `furnayce` ×4, `amiance` ×4, `mackefellyn` ×4, `anioue` ×4, `alquers` ×4
