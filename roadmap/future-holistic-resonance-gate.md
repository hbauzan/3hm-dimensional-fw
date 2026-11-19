# Future holistic resonance gate

Out of scope for v0.2.x. Not implemented.

The current Tier-3 gate is an unweighted K-of-D count. A coordinate inside the stored interval `[lo_d, hi_d]` contributes one vote. The primary lock passes when the vote count reaches K = 103. Pairwise locks on the live gateway stay on that unweighted path.

A future scorer weights each active dimension by the stored width `(hi_d - lo_d)`. A narrow interval would weigh more than a wide interval. v0.2.x does not apply that weight, does not change K, and does not retune the live gate.
