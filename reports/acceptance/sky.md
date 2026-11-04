# Acceptance test 3: sky figures for Penge (Old Style dates)

Tolerance 2 minutes. Mine: PyEphem 4.2.1; 51.415 N, 0.060 W; sea-level horizon;
upper limb with 34' refraction; sunrise/sunset in local apparent (sundial) time, twilight in
local mean time; Delta T from libastro (Morrison & Stephenson 2004 before 1700: about 129 s in
1589, 21 s in 1689). The last column shows what a horizon of -0 deg 47' (13' lower) would give.

| date | event | Henry | mine | mine - Henry (min) | 2-min test | at -0:47 |
|---|---|---:|---:|---:|---|---:|
| 1 May 1689 | sunset (sundial) | 7.45 | 7.44 | -1.5 | pass | +0.2 |
| 1 May 1689 | end of civil twilight (LMT) | 8.20 | 8.20 | +0.1 | pass |  |
| 9 May 1689 | sunset (sundial) | 7.57 | 7.55 | -1.8 | pass | -0.1 |
| 9 May 1689 | end of civil twilight (LMT) | 8.33 | 8.34 | +0.9 | pass |  |
| 25 May 1689 | sunset (sundial) | 8.14 | 8.13 | -1.4 | pass | +0.4 |
| 25 May 1689 | end of civil twilight (LMT) | 8.56 | 8.57 | +0.6 | pass |  |
| 24 June 1689 | sunset (sundial) | 8.16 | 8.14 | -1.9 | pass | -0.0 |
| 24 June 1689 | end of civil twilight (LMT) | 9.04 | 9.04 | +0.5 | pass |  |
| 15 July 1689 | sunset (sundial) | 7.53 | 7.51 | -1.6 | pass | +0.1 |
| 15 July 1689 | end of civil twilight (LMT) | 8.39 | 8.39 | +0.2 | pass |  |
| 1 August 1689 | sunset (sundial) | 7.26 | 7.24 | -1.8 | pass | -0.3 |
| 1 August 1689 | end of civil twilight (LMT) | 8.06 | 8.07 | +0.7 | pass |  |
| 29 September 1689 | sunset (sundial) | 5.33 | 5.32 | -1.5 | pass | -0.1 |
| 29 September 1689 | end of civil twilight (LMT) | 5.51 | 5.52 | +0.9 | pass |  |
| 1 April 1589 | sunrise (sundial) | 5.10 | 5.13 | +2.5 | **outside** | +1.1 |
| 1 April 1589 | sunset (sundial) | 6.50 | 6.49 | -1.4 | pass | +0.0 |
| 1 May 1589 | sunrise (sundial) | 4.16 | 4.19 | +2.7 | **outside** | +1.1 |
| 1 May 1589 | sunset (sundial) | 7.44 | 7.42 | -1.7 | pass | -0.1 |

16 of 18 within tolerance.

| moon 1589 | Henry | mine | |
|---|---|---|---|
| new moon | 4 April | 4 April 23:22 LMT | pass |
| full moon | 20 April | 20 April 12:10 LMT | pass |
| new moon | 4 May | 4 May 11:41 LMT | pass |
| full moon | 19 May | 19 May 20:55 LMT | pass |

Easter: 1589 Henry 30 March, mine 30 March 1589; 1689 Henry 31 March, mine 31 March 1689 (Julian computus).

## Discrepancies, and which I believe

All seven 1689 sunsets come out 1.4-1.9 minutes earlier than Henry's, inside the tolerance but
always on the same side; the twilight times agree to a minute. Both 1589 sunrises are 2.5-2.7
minutes later than his, outside the tolerance, while the 1589 sunsets are 1.4-1.7 minutes earlier.

Two things account for this. First, Henry's figures behave as if the horizon were about 13'
lower than the standard sea-level horizon (an observer some 55 m up, which is roughly the height
of the Common, would see that much dip): with the horizon at -0 deg 47' every sunset agrees to
within half a minute. Second, Henry's sunrises are exact mirror images of his sunsets about
12.00 (5.10/6.50, 4.16/7.44), whereas in April and May the Sun's declination rises through the
day, so the true morning arc is about a minute shorter than the afternoon one; that leaves his
two sunrises about a minute early even on the lower horizon.

I believe my figures for the stated convention (sea-level horizon, standard refraction), which
is the almanac convention and what the desk prints. For what someone on the Common actually saw,
neither set is exact: the real horizon was hills, trees and buildings, which delay the visible
sunrise and hasten the visible sunset by more than either effect above. I have not changed my
convention to match, and have not adjusted Henry's figures.
